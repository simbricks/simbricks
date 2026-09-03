# Packer template for layered SimBricks images, vendored from image-builder's
# image.pkr.hcl. It boots @source_image and runs @scripts in the guest.
# Everything it runs is composed by
# simbricks.imagebuild.packer; keep the two in sync when image-builder changes.

packer {
  required_plugins {
    qemu = {
      source  = "github.com/hashicorp/qemu"
      version = "~> 1.1"
    }
  }
}

# ---- Inputs -----------------------------------------------------------------

variable "source_image" {
  type        = string
  description = "Local path or URL of the image to build on top of."
}

variable "source_checksum" {
  type        = string
  default     = "none"
  description = "Checksum for source_image. 'none' for the local files we normally hand it."
}

variable "name" {
  type        = string
  default     = "image"
  description = "Image name; also the disk filename."
}

variable "output" {
  type        = string
  description = "Output directory. Packer requires it not to exist yet."
}

variable "scripts" {
  type        = list(string)
  default     = []
  description = "Guest scripts, run in order. The layers lower to these."
}

variable "input" {
  type        = string
  default     = ""
  description = "Optional local tarball, unpacked to /tmp/input before the scripts run."
}

variable "cleanup_script" {
  type        = string
  default     = ""
  description = "Script run last, after the layers. Empty skips it."
}

variable "serial_log" {
  type        = string
  default     = ""
  description = "File to write the guest's serial console to. The only view into a boot that never reaches SSH."
}

variable "seed_files" {
  type        = list(string)
  description = "cloud-init NoCloud seed (user-data, meta-data, network-config), attached as a CD."
}

variable "disk_size" {
  type    = string
  default = "8G"
}

variable "memory" {
  type    = number
  default = 2048
}

variable "cpus" {
  type    = number
  default = 2
}

variable "qemu_binary" {
  type    = string
  default = "qemu-system-x86_64"
}

variable "accelerator" {
  type        = string
  default     = "kvm"
  description = "'tcg' where there is no /dev/kvm, at a large cost in build time."
}

variable "ssh_username" {
  type    = string
  default = "ubuntu"
}

variable "ssh_password" {
  type    = string
  default = "ubuntu"
}

variable "ssh_timeout" {
  type    = string
  default = "20m"
}

variable "http_proxy" {
  type    = string
  default = env("http_proxy")
}

variable "https_proxy" {
  type    = string
  default = env("https_proxy")
}

# ---- Builder ----------------------------------------------------------------

locals {
  # Run each script as root, forwarding any proxy.
  execute_command = "chmod +x {{.Path}}; sudo -E env {{.Vars}} http_proxy=${var.http_proxy} https_proxy=${var.https_proxy} {{.Path}}"
}

source "qemu" "image" {
  iso_url          = var.source_image
  iso_checksum     = var.source_checksum
  disk_image       = true
  disk_size        = var.disk_size
  format           = "qcow2"
  accelerator      = var.accelerator
  qemu_binary      = var.qemu_binary
  memory           = var.memory
  cpus             = var.cpus
  headless         = true
  net_device       = "virtio-net"
  disk_interface   = "virtio"
  disk_compression = false

  # A local seed rather than image-builder's seedfrom=http://: cloud-init reads
  # a local seed in its init-local stage, before it configures the network. Over
  # HTTP it cannot, and on an image carrying dummy/bond interfaces its fallback
  # config picks one of those, leaving the real NIC down and the seed forever
  # unreachable. The guest kernel therefore needs iso9660.
  cd_files = var.seed_files
  cd_label = "cidata"

  qemuargs = var.serial_log == "" ? [] : [
    ["-serial", "file:${var.serial_log}"],
  ]

  ssh_username = var.ssh_username
  ssh_password = var.ssh_password
  ssh_timeout  = var.ssh_timeout

  shutdown_command = "sudo shutdown -P now"
  output_directory = var.output
  vm_name          = var.name
}

# ---- Build ------------------------------------------------------------------

build {
  sources = ["source.qemu.image"]

  # 1. optional: upload + unpack a local tarball to /tmp/input, which the layer
  #    scripts read the files their layers carry from.
  dynamic "provisioner" {
    for_each = var.input == "" ? [] : [var.input]
    labels   = ["file"]
    content {
      source      = provisioner.value
      destination = "/tmp/input.tar.gz"
    }
  }
  dynamic "provisioner" {
    for_each = var.input == "" ? [] : [var.input]
    labels   = ["shell"]
    content {
      inline = ["mkdir -p /tmp/input", "tar xzf /tmp/input.tar.gz -C /tmp/input"]
    }
  }

  # 2. the layers themselves, in order.
  dynamic "provisioner" {
    for_each = length(var.scripts) == 0 ? [] : [var.scripts]
    labels   = ["shell"]
    content {
      scripts         = provisioner.value
      execute_command = local.execute_command
    }
  }

  # 3. sanitize + shrink, last.
  dynamic "provisioner" {
    for_each = var.cleanup_script == "" ? [] : [var.cleanup_script]
    labels   = ["shell"]
    content {
      script          = provisioner.value
      execute_command = local.execute_command
    }
  }
}

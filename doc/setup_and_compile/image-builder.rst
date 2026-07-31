..
  Copyright 2026 Max Planck Institute for Software Systems,
  National University of Singapore, and SimBricks UG (haftungsbeschraenkt)
..
  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:
..
  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.
..
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

.. _sec-image-builder:

Building Disk Images
********************

Full-system host simulators boot Linux from a disk image (see :ref:`sec-disk-images` for how disk
images are referenced from virtual prototype scripts). Disk image building lives in its own small,
simulator-independent repository: :image-builder:`\ `. It drives :packer:`\ ` and QEMU to turn a
stock cloud image into the image plus boot artifacts SimBricks needs.

.. note::
  You only need this if you execute simulations on your own machines with custom images. The
  SimBricks Cloud Runners and the ``simbricks/simbricks-executor`` Docker image already ship a
  pre-built ``base`` image with the common drivers and tools included.

What it produces
================

A build produces one directory that maps 1:1 onto the global input directory layout the
orchestration framework expects:

.. code-block:: text

  output-base/
    base            # the disk image (qcow2)
    base.raw        # raw conversion (with CONVERT_RAW=true; required for gem5)
    boot/
      vmlinuz       # kernel (bzImage)  -> used by QEMU
      initrd        # initramfs         -> used by QEMU
      vmlinux       # kernel (ELF)      -> used by gem5

Copy (or symlink) this into your global input directory as ``images/<name>/`` and reference it
with ``system.DistroDiskImage(syst, "<name>")``.

Requirements and basic usage
============================

You need :packer:`\ ` (with the QEMU plugin), ``qemu-system-x86_64``/``qemu-img`` (KVM strongly
recommended), and libguestfs-tools. Alternatively, the repository ships a dev container with
everything pre-installed. Then:

.. code-block:: bash

  git clone https://github.com/simbricks/image-builder.git
  cd image-builder
  make image                       # builds the default Ubuntu-based 'base' image

The build boots the distro cloud image under QEMU, runs a configurable list of provisioning
scripts inside the guest (installing the generic kernel, base benchmarking tools, serial-console
boot configuration, and the SimBricks guest-init hook), and finally extracts the boot artifacts
from the finished image. Variables like ``SOURCE_IMAGE``/``SOURCE_CHECKSUM`` (base cloud image),
``NAME``, ``DISK_SIZE``, ``ACCELERATOR`` (``kvm``/``tcg``) and ``CONVERT_RAW`` can be overridden
on the ``make`` command line — see the repository README for the full list.

.. important::
  gem5 only supports raw images, so build with ``CONVERT_RAW=true`` if you plan to use ``Gem5Sim``.

Custom images
=============

There are two ways to customize images, both driven by additional provisioning scripts that run
inside the guest as root:

**One-shot** — append extra scripts to the base build:

.. code-block:: bash

  make image EXTRA_SCRIPTS="path/to/your/install-script.sh"

**Layered** — build the base once, then derive specialized images from it (faster when you
maintain several images):

.. code-block:: bash

  make image                                     # 1. base image -> output-base/base
  make image NAME=my-image \
      SOURCE_IMAGE=output-base/base SOURCE_CHECKSUM=none \
      BASE_SCRIPTS= EXTRA_SCRIPTS="path/to/your/install-script.sh"

Component repositories that need guest-side software ship such install scripts — e.g. the
Corundum ``mqnic`` driver (``examples/corundum/install-mqnic.sh``, which builds the driver against
the image's kernel) and gem5's ``m5`` guest tool (``examples/gem5/install-m5.sh``). See
:ref:`sec-simulator-integration-packaging` for how this fits into a simulator integration.

Custom kernels (gem5)
=====================

By default images use the distribution's own kernel. For gem5, the repository can additionally
build a custom kernel that boots without an initrd and includes timer patches for gem5:

.. code-block:: bash

  make kernel                          # -> output/kernel/{vmlinux, linux-*.deb}
  make image NAME=gem5 INPUT=output/kernel \
    BASE_SCRIPTS="kernel/install-kernel.sh scripts/install-base.sh scripts/configure-boot.sh scripts/install-guestinit.sh" \
    EXTRA_SCRIPTS="examples/gem5/install-m5.sh" \
    CONVERT_RAW=true

This is also exactly how the ``base`` image shipped in the executor Docker image is built.

In-script image builds
======================

Instead of building images ahead of time, virtual prototype scripts can also reference a Packer
configuration directly through ``system.PackerDiskImage(syst, <path-to-config>)`` — the image is
then built as part of preparing the simulation.

PACKER_VERSION := 1.6.0
KERNEL_VERSION := 5.4.46

IMAGE := output-ubuntu1804/ubuntu1804

all: $(IMAGE) $(IMAGE).raw vmlinux bzImage mqnic/mqnic.ko

clean:
	rm -rf packer packer_cache output-ubuntu1804 vmlinux bzImage \
	    mqnic/mqnic.ko mqnic/*.o mqnic/.*.cmd mqnic/mqnic.mod.c \
	    mqnic/Module.symvers mqnic/modules.order \
	    kernel/linux-5.4.46/

################################################
# Disk image

$(IMAGE).raw: $(IMAGE)
	qemu-img convert -f qcow2 -O raw $< $@

$(IMAGE): $(wildcard scripts/*) packer ubuntu1804.json
	rm -rf output-ubuntu1804
	./packer build ubuntu1804.json

packer:
	wget https://releases.hashicorp.com/packer/$(PACKER_VERSION)/packer_$(PACKER_VERSION)_linux_amd64.zip
	unzip packer_$(PACKER_VERSION)_linux_amd64.zip
	rm -f packer_$(PACKER_VERSION)_linux_amd64.zip


################################################
# Kernel

vmlinux bzImage &: kernel/linux-$(KERNEL_VERSION)
	$(MAKE) -C kernel/linux-$(KERNEL_VERSION)
	cp kernel/linux-$(KERNEL_VERSION)/vmlinux vmlinux
	cp kernel/linux-$(KERNEL_VERSION)/arch/x86_64/boot/bzImage bzImage

kernel/linux-$(KERNEL_VERSION):
	wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-$(KERNEL_VERSION).tar.xz
	tar xf linux-$(KERNEL_VERSION).tar.xz
	rm -f linux-$(KERNEL_VERSION).tar.xz
	mv linux-$(KERNEL_VERSION) kernel/
	cd kernel/linux-$(KERNEL_VERSION) && patch -p1 < ../linux-$(KERNEL_VERSION)-timers-gem5.patch
	cp kernel/config-$(KERNEL_VERSION) kernel/linux-$(KERNEL_VERSION)/.config

################################################
# mqnic kernel module

mqnic/mqnic.ko: vmlinux
	$(MAKE) -C kernel/linux-$(KERNEL_VERSION) M=`pwd`/mqnic/ modules
	touch $@

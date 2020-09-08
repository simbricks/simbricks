PACKER_VERSION := 1.6.0
KERNEL_VERSION := 5.4.46

BASE_IMAGE := output-ubuntu1804-base/ubuntu1804-base
NOPAXOS_IMAGE := output-nopaxos/nopaxos
MTCP_IMAGE := output-mtcp/mtcp
IMAGES := $(BASE_IMAGE) $(NOPAXOS_IMAGE) $(MTCP_IMAGE)
RAW_IMAGES := $(addsuffix .raw,$(IMAGES))

all: $(IMAGES) $(RAW_IMAGES) vmlinux bzImage mqnic/mqnic.ko

clean:
	rm -rf packer packer_cache output-ubuntu1804 vmlinux bzImage \
	    mqnic/mqnic.ko mqnic/*.o mqnic/.*.cmd mqnic/mqnic.mod.c \
	    mqnic/Module.symvers mqnic/modules.order \
	    kernel/linux-$(KERNEL_VERSION)/ kheaders.tar.bz2

################################################
# Disk image

%.raw: %
	qemu-img convert -f qcow2 -O raw $< $@

$(BASE_IMAGE): $(wildcard scripts/*) packer ubuntu1804-base.json bzImage kheaders.tar.bz2
	rm -rf output-ubuntu1804-base
	./packer build ubuntu1804-base.json
	touch $@

$(NOPAXOS_IMAGE): $(wildcard scripts/*) packer nopaxos.json $(BASE_IMAGE) scripts/install-nopaxos.sh
	rm -rf output-nopaxos
	./packer build nopaxos.json
	touch $@

$(MTCP_IMAGE): $(wildcard scripts/*) packer mtcp.json $(BASE_IMAGE) scripts/install-mtcp.sh
	rm -rf output-mtcp
	./packer build mtcp.json
	touch $@

packer:
	wget https://releases.hashicorp.com/packer/$(PACKER_VERSION)/packer_$(PACKER_VERSION)_linux_amd64.zip
	unzip packer_$(PACKER_VERSION)_linux_amd64.zip
	rm -f packer_$(PACKER_VERSION)_linux_amd64.zip


################################################
# Kernel

KERNEL_DIR := kernel/linux-$(KERNEL_VERSION)

$(KERNEL_DIR)/vmlinux: $(KERNEL_DIR)/.config
	$(MAKE) -C $(KERNEL_DIR)
	touch $@

vmlinux: $(KERNEL_DIR)/vmlinux
	cp kernel/linux-$(KERNEL_VERSION)/vmlinux vmlinux
	touch $@

# this dependency is a bit stupid, but not sure how to better do this
bzImage: $(KERNEL_DIR)/vmlinux
	cp $(KERNEL_DIR)/arch/x86_64/boot/bzImage bzImage
	touch $@

kheaders.tar.bz2:
	rm -rf ./kernel/kheaders
	mkdir -p ./kernel/kheaders
	$(MAKE) -C $(KERNEL_DIR) headers_install INSTALL_HDR_PATH=$(abspath ./kernel/kheaders/usr)
	$(MAKE) -C $(KERNEL_DIR) modules_install INSTALL_MOD_PATH=$(abspath ./kernel/kheaders)
	rm -f ./kernel/kheaders/lib/modules/$(KERNEL_VERSION)/build
	ln -s /usr/src/linux-headers-$(KERNEL_VERSION) \
	    ./kernel/kheaders/lib/modules/$(KERNEL_VERSION)/build
	rm -f ./kernel/kheaders/lib/modules/$(KERNEL_VERSION)/source
	mkdir -p ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)
	cp -r $(KERNEL_DIR)/.config $(KERNEL_DIR)/Makefile \
	    $(KERNEL_DIR)/Module.symvers $(KERNEL_DIR)/scripts \
	    $(KERNEL_DIR)/include \
	    ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)/
	mkdir -p ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)/tools/objtool/
	cp $(KERNEL_DIR)/tools/objtool/objtool \
	    ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)/tools/objtool/
	mkdir -p ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)/arch/x86/
	cp -r $(KERNEL_DIR)/arch/x86/Makefile \
	    $(KERNEL_DIR)/arch/x86/Makefile_32.cpu \
	    $(KERNEL_DIR)/arch/x86/Makefile.um \
	    $(KERNEL_DIR)/arch/x86/include \
	    ./kernel/kheaders/usr/src/linux-headers-$(KERNEL_VERSION)/arch/x86
	cd ./kernel/kheaders && tar cjf ../../$@ .

kernel/linux-$(KERNEL_VERSION)/.config: kernel/config-$(KERNEL_VERSION)
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

# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

include mk/subdir_pre.mk

PACKER_VERSION := 1.6.0
KERNEL_VERSION := 5.4.46

UBUNTU_IMAGE := $(d)output-ubuntu1804/ubuntu1804
BASE_IMAGE := $(d)output-base/base
NOPAXOS_IMAGE := $(d)output-nopaxos/nopaxos
MTCP_IMAGE := $(d)output-mtcp/mtcp
TAS_IMAGE := $(d)output-tas/tas
IMAGES := $(UBUNTU_IMAGE) $(BASE_IMAGE) $(NOPAXOS_IMAGE)
RAW_IMAGES := $(addsuffix .raw,$(IMAGES))

img_dir := $(d)
packer := $(d)packer

bz_image := $(d)bzImage
vmlinux := $(d)vmlinux
kernel_pardir := $(d)kernel
kernel_dir := $(kernel_pardir)/linux-$(KERNEL_VERSION)
kheader_dir := $(d)kernel/kheaders
mqnic_dir := $(d)mqnic
mqnic_mod := $(mqnic_dir)/mqnic.ko

build-images: $(IMAGES) $(RAW_IMAGES) $(vmlinux) $(bz_image) $(mqnic_mod)

################################################
# Disk image

%.raw: %
	$(QEMU_IMG) convert -f qcow2 -O raw $< $@

$(UBUNTU_IMAGE): $(packer) $(QEMU) $(addprefix $(d),ubuntu1804.json \
    scripts/vagrant.sh scripts/sshd.sh scripts/update.sh scripts/packages.sh \
    scripts/cleanup.sh scripts/preseed.cfg)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh build ubuntu1804.json
	touch $@

$(BASE_IMAGE): $(packer) $(QEMU) $(d)base.json $(UBUNTU_IMAGE) $(bz_image) \
    $(d)kheaders.tar.bz2 $(d)scripts/guestinit.sh
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh build base.json
	touch $@

$(NOPAXOS_IMAGE): $(packer) $(QEMU) $(d)nopaxos.json $(BASE_IMAGE) \
    $(addprefix $(d), scripts/install-nopaxos.sh nopaxos.config)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh build nopaxos.json
	touch $@

$(MTCP_IMAGE): $(packer) $(QEMU) $(d)mtcp.json $(BASE_IMAGE) \
    $(d)scripts/install-mtcp.sh
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh build mtcp.json
	touch $@

$(TAS_IMAGE): $(packer) $(QEMU) $(d)tas.json $(BASE_IMAGE) \
    $(d)scripts/install-tas.sh
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh build tas.json
	touch $@

$(packer):
	wget -O $(img_dir)packer_$(PACKER_VERSION)_linux_amd64.zip https://releases.hashicorp.com/packer/$(PACKER_VERSION)/packer_$(PACKER_VERSION)_linux_amd64.zip
	cd $(img_dir) && unzip packer_$(PACKER_VERSION)_linux_amd64.zip
	rm -f $(img_dir)packer_$(PACKER_VERSION)_linux_amd64.zip


################################################
# Kernel

$(kernel_dir)/vmlinux: $(kernel_dir)/.config
	$(MAKE) -C $(kernel_dir)
	touch $@

$(vmlinux): $(kernel_dir)/vmlinux
	cp $< $@
	touch $@

# this dependency is a bit stupid, but not sure how to better do this
$(bz_image): $(kernel_dir)/vmlinux
	cp $(kernel_dir)/arch/x86_64/boot/bzImage $@
	touch $@

$(d)kheaders.tar.bz2: $(kernel_dir)/vmlinux
	rm -rf $(kheader_dir)
	mkdir -p $(kheader_dir)
	$(MAKE) -C $(kernel_dir) headers_install INSTALL_HDR_PATH=$(abspath $(kheader_dir)/usr)
	$(MAKE) -C $(kernel_dir) modules_install INSTALL_MOD_PATH=$(abspath $(kheader_dir))
	rm -f $(kheader_dir)/lib/modules/$(KERNEL_VERSION)/build
	ln -s /usr/src/linux-headers-$(KERNEL_VERSION) \
	    $(kheader_dir)/lib/modules/$(KERNEL_VERSION)/build
	rm -f $(kheader_dir)/lib/modules/$(KERNEL_VERSION)/source
	mkdir -p $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)
	cp -r $(kernel_dir)/.config $(kernel_dir)/Makefile \
	    $(kernel_dir)/Module.symvers $(kernel_dir)/scripts \
	    $(kernel_dir)/include \
	    $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)/
	mkdir -p $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)/tools/objtool/
	cp $(kernel_dir)/tools/objtool/objtool \
	    $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)/tools/objtool/
	mkdir -p $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)/arch/x86/
	cp -r $(kernel_dir)/arch/x86/Makefile \
	    $(kernel_dir)/arch/x86/Makefile_32.cpu \
	    $(kernel_dir)/arch/x86/Makefile.um \
	    $(kernel_dir)/arch/x86/include \
	    $(kheader_dir)/usr/src/linux-headers-$(KERNEL_VERSION)/arch/x86
	cd $(kheader_dir) && tar cjf $(abspath $@) .

$(kernel_dir)/.config: $(kernel_pardir)/config-$(KERNEL_VERSION)
	rm -rf $(kernel_dir)
	wget -O - https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-$(KERNEL_VERSION).tar.xz | \
	    tar xJf - -C $(kernel_pardir)
	cd $(kernel_dir) && patch -p1 < ../linux-$(KERNEL_VERSION)-timers-gem5.patch
	cp $< $@

################################################
# mqnic kernel module

$(mqnic_mod): $(vmlinux)
	$(MAKE) -C $(kernel_dir) M=$(abspath $(mqnic_dir)) modules
	touch $@


CLEAN := $(addprefix $(d), mqnic/mqnic.ko mqnic/*.o mqnic/.*.cmd mqnic/*.mod \
    mqnic/mqnic.mod.c mqnic/Module.symvers mqnic/modules.order)

DISTCLEAN := $(kernel_dir) $(packer) $(bz_image) $(vmlinux) $(kheader_dir) \
    $(foreach i,$(IMAGES),$(dir $(i))) \
    $(d)packer_cache $(d)kheaders.tar.bz2

include mk/subdir_post.mk

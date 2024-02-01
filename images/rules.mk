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

PACKER_VERSION := 1.7.0
KERNEL_VERSION := 5.17.7

BASE_IMAGE := $(d)output-base/base
MEMCACHED_IMAGE := $(d)output-memcached/memcached
NOPAXOS_IMAGE := $(d)output-nopaxos/nopaxos
MTCP_IMAGE := $(d)output-mtcp/mtcp
TAS_IMAGE := $(d)output-tas/tas
HOMA_IMAGE := $(d)output-homa/homa
TIMESYNC_IMAGE := $(d)output-timesync/timesync
HOMA_IMAGE := $(d)output-homa/homa
COMPRESSED_IMAGES ?= false

IMAGES := $(BASE_IMAGE) $(NOPAXOS_IMAGE) $(MEMCACHED_IMAGE) $(TIMESYNC_IMAGE) \
  $(HOMA_IMAGE)
RAW_IMAGES := $(addsuffix .raw,$(IMAGES))

IMAGES_MIN := $(BASE_IMAGE)
RAW_IMAGES_MIN := $(addsuffix .raw,$(IMAGES_MIN))

img_dir := $(d)
packer := $(d)packer

bz_image := $(d)bzImage
vmlinux := $(d)vmlinux
kernel_pardir := $(d)kernel
kernel_dir := $(kernel_pardir)/linux-$(KERNEL_VERSION)
kernel_config := $(kernel_pardir)/config-$(KERNEL_VERSION)
kheader_dir := $(d)kernel/kheaders
kheader_tar := $(d)kheaders.tar.bz2
mqnic_dir := $(d)mqnic
mqnic_mod := $(mqnic_dir)/mqnic.ko
farmem_dir := $(d)farmem
farmem_mod := $(farmem_dir)/farmem.ko
m5_bin := $(d)m5
guest_init := $(d)/scripts/guestinit.sh
homa_dir := $(d)homa
homa_mod := $(homa_dir)/homa.ko

build-images: $(IMAGES) $(RAW_IMAGES) $(vmlinux) $(bz_image) $(mqnic_mod) \
  $(farmem_mod)

build-images-min: $(IMAGES_MIN) $(RAW_IMAGES_MIN) $(vmlinux) $(bz_image) \
    $(mqnic_mod) $(farmem_mod)

# only converts existing images to raw
convert-images-raw:
	for i in $(IMAGES); do \
	    [ -f $$i ] || continue; \
	    $(QEMU_IMG) convert -f qcow2 -O raw $$i $${i}.raw ; done

################################################
# Disk image

%.raw: %
	$(QEMU_IMG) convert -f qcow2 -O raw $< $@

$(BASE_IMAGE): $(packer) $(QEMU) $(bz_image) $(m5_bin) $(kheader_tar) \
    $(guest_init) $(kernel_config) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-base.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	mkdir -p $(img_dir)/input-base
	cp $(m5_bin) $(kheader_tar) $(guest_init) $(bz_image) $(kernel_config) \
	    $(img_dir)/input-base/
	cd $(img_dir) && ./packer-wrap.sh base base base.pkr.hcl \
	    $(COMPRESSED_IMAGES)
	rm -rf $(img_dir)/input-base
	touch $@

$(MEMCACHED_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-memcached.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh base memcached \
	    extended-image.pkr.hcl $(COMPRESSED_IMAGES)
	rm -rf $(img_dir)/input-base
	touch $@

$(NOPAXOS_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-nopaxos.sh \
      scripts/cleanup.sh nopaxos.config)
	rm -rf $(dir $@)
	mkdir -p $(img_dir)/input-nopaxos
	cp $(img_dir)/nopaxos.config $(img_dir)/input-nopaxos/
	cd $(img_dir) && ./packer-wrap.sh base nopaxos extended-image.pkr.hcl \
	    $(COMPRESSED_IMAGES)
	touch $@

$(MTCP_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-mtcp.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh base mtcp extended-image.pkr.hcl \
	    $(COMPRESSED_IMAGES)
	touch $@

$(TAS_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-tas.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh base tas extended-image.pkr.hcl \
	    $(COMPRESSED_IMAGES)
	touch $@

$(TIMESYNC_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-timesync.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	cd $(img_dir) && ./packer-wrap.sh base timesync extended-image.pkr.hcl \
	    $(COMPRESSED_IMAGES)
	touch $@

$(HOMA_IMAGE): $(packer) $(QEMU) $(BASE_IMAGE) \
    $(addprefix $(d), extended-image.pkr.hcl scripts/install-homa.sh \
      scripts/cleanup.sh)
	rm -rf $(dir $@)
	mkdir -p $(img_dir)/input-homa
	cp -r $(homa_dir) \
	    $(img_dir)/input-homa
	cd $(img_dir) && ./packer-wrap.sh base homa extended-image.pkr.hcl \
	$(COMPRESSED_IMAGES)
	rm -rf $(img_dir)/input-homa
	touch $@

$(packer):
	wget -O $(img_dir)packer_$(PACKER_VERSION)_linux_amd64.zip \
	    https://releases.hashicorp.com/packer/$(PACKER_VERSION)/packer_$(PACKER_VERSION)_linux_amd64.zip
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

$(kheader_tar): $(kernel_dir)/vmlinux
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

# HOMA kernel module
$(homa_mod): $(vmlinux)
	$(MAKE) -C $(kernel_dir) M=$(abspath $(homa_dir)) modules
	touch $@

################################################
# homa kernel module

$(homa_dir):
	git clone https://github.com/PlatformLab/HomaModule \
	    -b linux_$(KERNEL_VERSION) $@

# HOMA kernel module
$(homa_mod): $(vmlinux) $(homa_dir)
	$(MAKE) -C $(kernel_dir) M=$(abspath $(homa_dir)) modules
	touch $@

################################################
# farmem kernel module

$(farmem_mod): $(vmlinux)
	$(MAKE) -C $(kernel_dir) M=$(abspath $(farmem_dir)) modules
	touch $@

CLEAN := $(addprefix $(d), mqnic/mqnic.ko mqnic/*.o mqnic/.*.cmd mqnic/*.mod \
    mqnic/mqnic.mod.c mqnic/Module.symvers mqnic/modules.order \
    farmem/farmem.ko farmem/*.o farmem/.*.cmd farmem/*.mod \
    farmem/farmem.mod.c farmem/Module.symvers farmem/modules.order)
DISTCLEAN := $(kernel_dir) $(packer) $(bz_image) $(vmlinux) $(kheader_dir) \
    $(foreach i,$(IMAGES),$(dir $(i)) $(subst output-,input-,$(dir $(i)))) \
    $(d)packer_cache $(d)kheaders.tar.bz2

include mk/subdir_post.mk

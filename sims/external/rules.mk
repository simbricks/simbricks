include mk/subdir_pre.mk

QEMU_IMG := $(d)qemu/build/qemu-img
QEMU := $(d)qemu/build/qemu-system-x86_64

external: $(d)gem5/ready $(d)qemu/ready $(d)ns-3/ready
.PHONY: external

$(d)gem5:
	git clone git@github.com:simbricks/gem5.git $@

$(d)gem5/ready: $(d)gem5
	+cd $< && scons build/X86/gem5.opt -j`nproc`
	touch $@


$(d)qemu:
	git clone git@github.com:simbricks/qemu.git $@

$(d)qemu/ready: $(d)qemu
	+cd $< && ./configure \
	    --target-list=x86_64-softmmu \
	    --disable-werror \
	    --extra-cflags="-I$(abspath $(lib_proto_inc))" \
	    --enable-cosim-pci && \
	  $(MAKE)
	touch $@

$(QEMUG_IMG): $(d)qemu/ready
	touch $@

$(QEMU): $(d)qemu/ready
	touch $@


$(d)ns-3:
	git clone git@github.com:simbricks/ns-3.git $@

$(d)ns-3/ready: $(d)ns-3 $(lib_netsim)
	+cd $< && COSIM_PATH=$(abspath $(base_dir)) ./cosim-build.sh configure
	touch $@

DISTCLEAN := $(base_dir)gem5 $(base_dir)qemu $(base_dir)ns-3
include mk/subdir_post.mk

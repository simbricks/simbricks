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

QEMU_IMG := $(d)qemu/build/qemu-img
QEMU := $(d)qemu/build/qemu-system-x86_64
GEM5_VARIANT ?= fast

EXTERNAL_SIMS_DIR := $(d)

$(eval $(call subdir,simics))

external: $(d)gem5/ready $(d)qemu/ready $(d)ns-3/ready $(d)femu/ready $(d)bmv2/ready
.PHONY: external gem5-clean qemu-clean ns-3-clean femu-clean bmv2-clean



$(d)gem5:
	git clone https://github.com/simbricks/gem5.git $@

$(d)gem5/ready: $(d)gem5
	cd $< && \
		CCFLAGS_EXTRA="-I$(abspath $(lib_dir))" \
		LIBRARY_PATH="$(abspath $(lib_dir))" \
		scons build/X86/gem5.$(GEM5_VARIANT) \
		--ignore-style -j`nproc`
	touch $@

gem5-clean:
	-cd $(EXTERNAL_SIMS_DIR)gem5 && scons --clean build/X86/gem5.$(GEM5_VARIANT)
	rm -f $(EXTERNAL_SIMS_DIR)gem5/ready


$(d)qemu:
	git clone https://github.com/simbricks/qemu.git $@

$(d)qemu/ready: $(d)qemu
	+cd $< && ./configure \
	    --target-list=x86_64-softmmu \
	    --disable-werror \
	    --with-pkgversion=SimBricks \
	    --extra-cflags="-I$(abspath $(lib_dir))" \
	    --extra-ldflags="-L$(abspath $(lib_dir))" \
	    --enable-simbricks \
	    --enable-simbricks-pci && \
	  $(MAKE)
	touch $@

$(QEMUG_IMG): $(d)qemu/ready
	touch $@

$(QEMU): $(d)qemu/ready
	touch $@

qemu-clean:
	-+cd $(EXTERNAL_SIMS_DIR)qemu && $(MAKE) clean
	rm -f $(EXTERNAL_SIMS_DIR)qemu/ready


$(d)ns-3:
	git clone https://github.com/simbricks/ns-3.git $@

$(d)ns-3/ready: $(d)ns-3 $(lib_netif)
	+cd $< && SIMBRICKS_PATH=$(abspath $(base_dir)) ./simbricks-build.sh configure
	touch $@

ns-3-clean:
	-cd $(EXTERNAL_SIMS_DIR)ns-3 && ./ns3 clean
	rm -f $(EXTERNAL_SIMS_DIR)ns-3/ready

$(d)femu:
	git clone https://github.com/simbricks/femu.git $@

$(d)femu/ready: $(d)femu $(lib_nicif)
	cd $< && make EXTRA_LDFLAGS="-L$(abspath $(lib_dir))/simbricks/nicif/ \
	      -L$(abspath $(lib_dir))/simbricks/pcie/ \
	      -L$(abspath $(lib_dir))/simbricks/base/ "\
	    EXTRA_CPPFLAGS=-I$(abspath $(lib_dir))
	touch $@

femu-clean:
	-+cd $(EXTERNAL_SIMS_DIR)femu && $(MAKE) clean
	rm -f $(EXTERNAL_SIMS_DIR)femu/ready

$(d)bmv2:
	git clone https://github.com/simbricks/bmv2.git $@

$(d)bmv2/ready: $(d)bmv2 $(lib_netif)
	+cd $< && ./autogen.sh && \
	CPPFLAGS=-I$(abspath $(lib_dir)) ./configure && \
	$(MAKE) -j
	touch $@

bmv2-clean:
	-cd $(EXTERNAL_SIMS_DIR)bmv2 && $(MAKE) clean
	rm -f $(EXTERNAL_SIMS_DIR)bmv2/ready

DISTCLEAN := $(d)gem5 $(d)qemu $(d)ns-3 $(d)femu
EXTERNAL_CLEAN_TASKS := gem5-clean qemu-clean ns-3-clean femu-clean bmv2-clean
include mk/subdir_post.mk

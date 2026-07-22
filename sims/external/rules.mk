# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
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

EXTERNAL_SIMS_DIR := $(d)

SIMBRICKS_INC_DIR ?= $(abspath $(lib_dir))
SIMBRICKS_LIB_DIR ?= $(abspath $(lib_dir))

PREFIX ?= /usr/local

$(eval $(call subdir,simics))

external: $(d)ns-3/ready $(d)bmv2/ready
.PHONY: external ns-3-clean bmv2-clean


$(d)ns-3:
	git clone https://github.com/simbricks/ns-3.git $@

$(d)ns-3/ready: $(d)ns-3 $(lib_netif)
	+cd $< && SIMBRICKS_PATH=$(abspath $(base_dir)) ./simbricks-build.sh configure
	touch $@

ns-3-clean:
	-cd $(EXTERNAL_SIMS_DIR)ns-3 && ./ns3 clean
	rm -f $(EXTERNAL_SIMS_DIR)ns-3/ready

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

DISTCLEAN := $(d)ns-3 $(d)femu
EXTERNAL_CLEAN_TASKS := ns-3-clean bmv2-clean
include mk/subdir_post.mk

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


dir_corundum := $(d)
bin_corundum := $(d)corundum_verilator
verilator_dir_corundum := $(d)obj_dir
verilator_src_corundum := $(verilator_dir_corundum)/Vinterface.cpp
verilator_bin_corundum := $(verilator_dir_corundum)/Vinterface

vsrcs_corundum := $(wildcard $(d)rtl/*.v $(d)lib/*/rtl/*.v \
    $(d)lib/*/lib/*/rtl/*.v)
srcs_corundum := $(addprefix $(d),corundum_verilator.cc dma.cc mem.cc)
OBJS := $(srcs_corundum:.cc=.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/

$(verilator_src_corundum): $(vsrcs_corundum)
	$(VERILATOR) $(VFLAGS) --cc -O3 \
	    -CFLAGS "-I$(abspath $(lib_dir)) -iquote $(abspath $(base_dir)) -O3 -g -Wall -Wno-maybe-uninitialized" \
	    --Mdir $(verilator_dir_corundum) \
	    -y $(dir_corundum)rtl \
	    -y $(dir_corundum)lib/axi/rtl \
	    -y $(dir_corundum)lib/eth/lib/axis/rtl/ \
	    -y $(dir_corundum)lib/pcie/rtl \
	    $(dir_corundum)rtl/interface.v --exe $(abspath $(srcs_corundum)) \
	      $(abspath $(lib_nicif) $(lib_netif) $(lib_pcie) $(lib_base))

$(verilator_bin_corundum): $(verilator_src_corundum) $(srcs_corundum) \
    $(lib_nicif)
	$(MAKE) -C $(verilator_dir_corundum) -f Vinterface.mk

$(bin_corundum): $(verilator_bin_corundum)
	cp $< $@

CLEAN := $(bin_corundum) $(verilator_dir_corundum) $(OBJS)
ALL := $(bin_corundum)
include mk/subdir_post.mk

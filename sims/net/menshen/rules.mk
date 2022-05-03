# Copyright 2022 Max Planck Institute for Software Systems, and
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


dir_menshen := $(d)
bin_menshen := $(d)menshen_hw
verilator_dir_menshen := $(d)obj_dir
verilator_src_menshen := $(verilator_dir_menshen)/Vrmt_wrapper.cpp
verilator_bin_menshen := $(verilator_dir_menshen)/Vrmt_wrapper

vsrcs_menshen := $(wildcard $(d)rtl/*.v $(d)lib/*/rtl/*.v \
    $(d)lib/*/lib/*/rtl/*.v)
srcs_menshen := $(addprefix $(d),menshen_hw.cc)
OBJS := $(srcs_menshen:.cc=.o)

#$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/

$(verilator_src_menshen): $(vsrcs_menshen)
	$(VERILATOR) $(VFLAGS) --cc -O3 \
	    -CFLAGS "-I$(abspath $(lib_dir)) -iquote $(abspath $(base_dir)) -O3 -g -Wall -Wno-maybe-uninitialized -fno-var-tracking-assignments" \
	    --Mdir $(verilator_dir_menshen) \
	    -y $(dir_menshen)rtl -y $(dir_menshen)rtl/extract \
	    -y $(dir_menshen)rtl/action  -y $(dir_menshen)rtl/lookup -y $(dir_menshen)lib \
	    $(dir_menshen)rtl/rmt_wrapper.v --exe $(abspath $(srcs_menshen)) \
		$(abspath $(lib_netif)) $(abspath $(lib_base))

$(verilator_bin_menshen): $(verilator_src_menshen) $(srcs_menshen) $(lib_netif)
	$(MAKE) -C $(verilator_dir_menshen) -f Vrmt_wrapper.mk

$(bin_menshen): $(verilator_bin_menshen)
	cp $< $@

CLEAN := $(bin_menshen) $(verilator_dir_menshen) $(OBJS)
ifeq ($(ENABLE_VERILATOR),y)
ALL := $(bin_menshen)
endif
include mk/subdir_post.mk

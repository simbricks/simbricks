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

bin_i40e_bm := $(d)i40e_bm

OBJS := $(addprefix $(d),i40e_bm.o i40e_queues.o i40e_adminq.o i40e_hmc.o \
    i40e_lan.o i40e_ptp.o xsums.o rss.o logger.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/

$(bin_i40e_bm): $(OBJS) $(lib_nicbm) $(lib_nicif) $(lib_netif) $(lib_pcie) \
    $(lib_base) -lboost_fiber -lboost_context -lpthread

CLEAN := $(bin_i40e_bm) $(OBJS)
ALL := $(bin_i40e_bm)
include mk/subdir_post.mk

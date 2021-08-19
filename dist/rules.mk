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

bin_net_rdma := $(d)rdma/net_rdma
bin_net_sockets := $(d)sockets/net_sockets

COMMON_OBJS := $(addprefix $(d)common/, net.o utils.o)
RDMA_OBJS := $(addprefix $(d)rdma/, net_rdma.o rdma.o rdma_cm.o rdma_ib.o)
SOCKETS_OBJS := $(addprefix $(d)sockets/, net_sockets.o)

$(bin_net_rdma): $(RDMA_OBJS) $(COMMON_OBJS) -lrdmacm -libverbs -lpthread
$(bin_net_sockets): $(SOCKETS_OBJS) $(COMMON_OBJS) -lpthread

CLEAN := $(bin_net_rdma) $(bin_net_sockets) \
	$(RDMA_OBJS) $(SOCKETS_OBJS) $(COMMON_OBJS)
ALL := $(bin_net_sockets)

ifeq ($(ENABLE_DIST),y)
ALL += $(bin_net_rdma)
endif

include mk/subdir_post.mk

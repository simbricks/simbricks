include mk/subdir_pre.mk

bin_net_switch := $(d)net_switch

OBJS := $(d)net_switch.o

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_netsim_inc)

$(bin_net_switch): $(OBJS) $(lib_netsim) -lpcap

CLEAN := $(bin_net_switch) $(OBJS)
ALL := $(bin_net_switch)
include mk/subdir_post.mk

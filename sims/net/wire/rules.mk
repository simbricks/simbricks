include mk/subdir_pre.mk

bin_net_wire := $(d)net_wire

OBJS := $(d)net_wire.o

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_netsim_inc)

$(bin_net_wire): $(OBJS) $(lib_netsim) -lpcap

CLEAN := $(bin_net_wire) $(OBJS)
ALL := $(bin_net_wire)
include mk/subdir_post.mk

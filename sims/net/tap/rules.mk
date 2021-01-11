include mk/subdir_pre.mk

bin_net_tap := $(d)net_tap

OBJS := $(d)net_tap.o

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_netsim_inc)

$(bin_net_tap): $(OBJS) $(lib_netsim) -lpcap -lpthread

CLEAN := $(bin_net_tap) $(OBJS)
ALL := $(bin_net_tap)
include mk/subdir_post.mk

include mk/subdir_pre.mk

lib_netsim := $(d)libnetsim_common.a
lib_netsim_inc := $(d)include/

OBJS := $(addprefix $(d),netsim.o utils.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(lib_netsim_inc) -I$(lib_proto_inc)

$(lib_netsim): $(OBJS)

CLEAN := $(lib_netsim) $(OBJS)
include mk/subdir_post.mk

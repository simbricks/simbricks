include mk/subdir_pre.mk

lib_nicsim := $(d)libnicsim_common.a
lib_nicsim_inc := $(d)include/

OBJS := $(addprefix $(d),nicsim.o utils.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(lib_nicsim_inc) -I$(lib_proto_inc)

$(lib_nicsim): $(OBJS)

CLEAN := $(lib_nicsim) $(OBJS)
include mk/subdir_post.mk

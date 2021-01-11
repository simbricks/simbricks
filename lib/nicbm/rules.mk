include mk/subdir_pre.mk

lib_nicbm := $(d)libnicbm.a
lib_nicbm_inc := $(d)include/

OBJS := $(addprefix $(d),nicbm.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(lib_nicbm_inc) -I$(lib_proto_inc) \
    -I$(lib_nicsim_inc)

$(lib_nicbm): $(OBJS)

CLEAN := $(lib_nicbm) $(OBJS)
include mk/subdir_post.mk

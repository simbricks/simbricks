include mk/subdir_pre.mk

bin_corundum_bm := $(d)corundum_bm
bin_corundum_bm_tester := $(d)tester

objs_corundum_bm := $(d)corundum_bm.o
objs_corundum_bm_tester := $(d)tester.o
OBJS := $(objs_corundum_bm) $(objs_corundum_bm_tester)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_nicbm_inc) -I$(lib_nicsim_inc)

$(bin_corundum_bm): $(objs_corundum_bm) $(lib_nicbm) $(lib_nicsim)
$(bin_corundum_bm_tester): $(objs_corundum_bm_tester) $(lib_nicbm) $(lib_nicsim)

CLEAN := $(bin_corundum_bm) $(bin_corundum_bm_tester) $(OBJS)
ALL := $(bin_corundum_bm)
include mk/subdir_post.mk

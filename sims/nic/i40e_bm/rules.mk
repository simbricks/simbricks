include mk/subdir_pre.mk

bin_i40e_bm := $(d)i40e_bm

OBJS := $(addprefix $(d),i40e_bm.o i40e_queues.o i40e_adminq.o i40e_hmc.o \
    i40e_lan.o xsums.o rss.o logger.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_nicbm_inc) -I$(lib_nicsim_inc)

$(bin_i40e_bm): $(OBJS) $(lib_nicbm) $(lib_nicsim)

CLEAN := $(bin_i40e_bm) $(OBJS)
ALL := $(bin_i40e_bm)
include mk/subdir_post.mk

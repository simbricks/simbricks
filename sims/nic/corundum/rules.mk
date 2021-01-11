include mk/subdir_pre.mk


dir_corundum := $(d)
bin_corundum := $(d)corundum_verilator
verilator_dir_corundum := $(d)obj_dir
verilator_src_corundum := $(verilator_dir_corundum)/Vinterface.cpp
verilator_bin_corundum := $(verilator_dir_corundum)/Vinterface

vsrcs_corundum := $(wildcard $(d)rtl/*.v $(d)lib/*/rtl/*.v \
    $(d)lib/*/lib/*/rtl/*.v)
srcs_corundum := $(addprefix $(d),corundum_verilator.cpp dma.cpp mem.cpp)
OBJS := $(srcs_corundum:.cpp=.o)

$(OBJS): CPPFLAGS := $(CPPFLAGS) -I$(d)include/ -I$(lib_proto_inc) \
    -I$(lib_nicbm_inc) -I$(lib_nicsim_inc)

$(verilator_src_corundum): $(vsrcs_corundum)
	$(VERILATOR) $(VFLAGS) --cc -O3 \
	    -CFLAGS "-I$(abspath $(lib_nicsim_inc)) -I$(abspath $(lib_proto_inc)) -O3 -g -Wall" \
	    --Mdir $(verilator_dir_corundum) \
	    -y $(dir_corundum)rtl \
	    -y $(dir_corundum)lib/axi/rtl \
	    -y $(dir_corundum)lib/eth/lib/axis/rtl/ \
	    -y $(dir_corundum)lib/pcie/rtl \
	    $(dir_corundum)rtl/interface.v --exe $(abspath $(srcs_corundum)) $(abspath $(lib_nicsim))

$(verilator_bin_corundum): $(verilator_src_corundum) $(srcs_corundum) \
    $(lib_nicsim)
	$(MAKE) -C $(verilator_dir_corundum) -f Vinterface.mk

$(bin_corundum): $(verilator_bin_corundum)
	cp $< $@

CLEAN := $(bin_corundum) $(verilator_dir_corundum) $(OBJS)
ALL := $(bin_corundum)
include mk/subdir_post.mk

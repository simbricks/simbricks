#$(warning leaving $(d))

DEPS := $(DEPS) $(OBJS:.o=.d)
CLEAN := $(CLEAN) $(DEPS)

CLEAN_ALL := $(CLEAN_ALL) $(CLEAN)
DISTCLEAN_ALL := $(DISTCLEAN_ALL) $(DISTCLEAN)
DEPS_ALL := $(DEPS_ALL) $(DEPS)
ALL_ALL := $(ALL_ALL) $(ALL)

ifeq "$(d)" ""
include mk/global.mk
-include $(DEPS_ALL)
else
endif

d := $(dirstack_$(sp))
sp := $(basename $(sp))

ALL :=
CLEAN :=
DISTCLEAN :=
DEPS :=
OBJS :=

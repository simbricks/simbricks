#$(warning entering $(cur_dir))

sp := $(sp).x
dirstack_$(sp) := $(d)
d := $(cur_dir)

ALL :=
CLEAN :=
DISTCLEAN :=
DEPS :=
OBJS :=

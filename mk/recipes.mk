# Generic recipes

# recurse into subdirectory (one parameter, subdirectory name)
define subdir
cur_dir := $$(d)$(1)/
$(if $(filter $(abspath .),$(abspath $$(d)$(1))),,include $$(cur_dir)rules.mk)
endef


DEPFLAGS ?= -MT $@ -MMD -MP -MF $(@:.o=.Td)
OUTPUT_OPTION.c ?= -o $@
OUTPUT_OPTION.cxx ?= -o $@
POSTCOMPILE_DEPS = mv -f $(@:.o=.Td) $(@:.o=.d)

# Compile C to object file while generating dependency
COMPILE.c = $(CC) $(DEPFLAGS) $(CFLAGS) $(CPPFLAGS) -c
%.o: %.c
%.o: %.c %.d
	$(COMPILE.c) $(OUTPUT_OPTION.c) $<
	@$(POSTCOMPILE_DEPS)

# Compile C to position independent object file while generating dependency
COMPILE_SHARED.c = $(CC) $(DEPFLAGS) $(CFLAGS_SHARED) $(CPPFLAGS) -c
%.shared.o: %.c
%.shared.o: %.c %.shared.d
	$(COMPILE_SHARED.c) $(OUTPUT_OPTION.c) $<
	@$(POSTCOMPILE_DEPS)

# Compile C++ to object file while generating dependency
COMPILE.cxx = $(CXX) $(DEPFLAGS) $(CXXFLAGS) $(CPPFLAGS) -c
%.o: %.cc
%.o: %.cc %.d
	$(COMPILE.cxx) $(OUTPUT_OPTION.cxx) $<
	@$(POSTCOMPILE_DEPS)

# Link binary from objects
LINK = $(CXX) $(LDFLAGS)
%: %.o
	$(LINK) $^ $(LDLIBS) -o $@

# Link shared library from objects
LINK.so = $(CC) $(LDFLAGS) -shared
%.so:
	$(LINK.so) $^ $(LDLIBS) $(OUTPUT_OPTION.c)

# create static library
LINK.a = $(AR) rcs
%.a:
	$(LINK.a) $@ $^

%.d: ;
.PRECIOUS: %.d

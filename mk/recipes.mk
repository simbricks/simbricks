# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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

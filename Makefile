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

include mk/subdir_pre.mk
include mk/recipes.mk

base_dir := $(d)./

CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC
CPPFLAGS += -I$(base_dir)/lib -iquote$(base_dir)

VERILATOR = verilator
VFLAGS = +1364-2005ext+v \
    -Wno-WIDTH -Wno-PINMISSING -Wno-LITENDIAN -Wno-IMPLICIT -Wno-SELRANGE \
    -Wno-CASEINCOMPLETE -Wno-UNSIGNED


$(eval $(call subdir,lib))
$(eval $(call subdir,sims))
$(eval $(call subdir,doc))
$(eval $(call subdir,images))


all: $(ALL_ALL)
.DEFAULT_GOAL := all

clean:
	rm -rf $(CLEAN_ALL)

distclean:
	rm -rf $(CLEAN_ALL) $(DISTCLEAN_ALL)

help:
	@echo "Targets:"
	@echo "  all: builds all the tools directly in this repo"
	@echo "  clean: cleans all the tool folders in this repo"
	@echo "  build-images: prepare prereqs for VMs (images directory)"
	@echo "  documentation: build documentation in doc/build_"
	@echo "  external: clone and build our tools in external repos "
	@echo "            (qemu, gem5, ns-3)"

.PHONY: all clean distclean help

include mk/subdir_post.mk
-include $(DEPS_ALL)

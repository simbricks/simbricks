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

-include mk/local.mk
include mk/subdir_pre.mk
include mk/recipes.mk

base_dir := $(d)./

CPPLINT ?= cpplint
CLANG_TIDY ?= clang-tidy
CLANG_FORMAT ?= clang-format
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC -std=gnu11 $(EXTRA_CFLAGS)
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC -std=gnu++17 $(EXTRA_CXXFLAGS)
CPPFLAGS += -I$(base_dir)/lib -iquote$(base_dir) $(EXTRA_CPPFLAGS)

$(eval $(call subdir,conda-recipes))
$(eval $(call subdir,docker))
$(eval $(call subdir,lib))
$(eval $(call subdir,dist))
$(eval $(call subdir,symphony))


all: $(ALL_ALL)
.DEFAULT_GOAL := all

clean:
	rm -rf $(CLEAN_ALL)

distclean:
	rm -rf $(CLEAN_ALL) $(DISTCLEAN_ALL)

lint-cpplint:
	$(CPPLINT) --quiet --recursive .

lint-clang-tidy:
	./.clang-tidy-wrapper.sh $(CLANG_TIDY) -I$(base_dir) -I$(base_dir)lib

clang-format:
	$(CLANG_FORMAT) -i --style=file `cat .lint-files`

lint-clang-format:
	$(CLANG_FORMAT) --Werror --dry-run --style=file `cat .lint-files`

lint-ruff:
	ruff check symphony/ experiments/ doc/
	ruff format --check symphony/ experiments/ doc/

format-ruff:
	ruff check --fix --exit-zero symphony/ experiments/ doc/
	ruff format symphony/ experiments/ doc/

lint-python: lint-ruff
format-python: format-ruff
lint: lint-cpplint lint-clang-format lint-python
lint-all: lint lint-clang-tidy

help:
	@echo "Targets:"
	@echo "  all: builds all the tools directly in this repo"
	@echo "  clean: cleans all the tool folders in this repo"
	@echo "  lint: run quick format and style checks"
	@echo "  lint-all: run slow & thorough format and style checks"
	@echo "  clang-format: reformat source (use with caution)"

.PHONY: all clean distclean lint lint-all \
	lint-cpplint lint-clang-tidy lint-clang-format clang-format help \
	lint-ruff format-ruff lint-python format-python

include mk/subdir_post.mk
-include $(DEPS_ALL)

# Copyright 2024 Max Planck Institute for Software Systems, and
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

SYMPHONY_DIR := $(d)/
SYMPHONY_MODS := utils orchestration client cli runtime runner local

SYMPHONY_PUBLICATION_REPO ?= testpypi

symphony-dev:
	pip install -r $(base_dir)requirements.txt
	cd $(SYMPHONY_DIR); pip install -r requirements.txt

symphony-build:
	for m in $(SYMPHONY_MODS); do \
		(cd $(SYMPHONY_DIR)$$m && \
		poetry build); \
	done

symphony-publish:
	for m in $(SYMPHONY_MODS); do \
		(cd $(SYMPHONY_DIR)$$m && \
		poetry publish -r $(SYMPHONY_PUBLICATION_REPO)); \
	done

.PHONY: symphony-dev symphony-build symphony-publish

CLEAN := $(addsuffix /dist, $(addprefix $(SYMPHONY_DIR), $(SYMPHONY_MODS)))
include mk/subdir_post.mk

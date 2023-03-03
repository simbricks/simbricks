# Copyright 2023 Max Planck Institute for Software Systems, and
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

SIMICS_DIR := $(d)

SIMICS_PKGMGR_DOWNLOAD ?= $(SIMICS_DIR)intel-simics-package-manager.tar.gz
SIMICS_ISPM_DOWNLOAD ?= $(SIMICS_DIR)simics-6-packages.ispm

SIMICS_ISPM := $(SIMICS_DIR)package-manager/ispm
SIMICS_INSTALLDIR := $(SIMICS_DIR)installdir
SIMICS_INSTALL := $(SIMICS_INSTALLDIR)/simics-latest
SIMICS_BIN := $(SIMICS_INSTALL)/bin
SIMICS_MODULES := $(SIMICS_DIR)modules
SIMICS_PROJECT := $(SIMICS_DIR)project

$(SIMICS_PKGMGR_DOWNLOAD):
	$(error Download intel-simics-package-manager-(version).tar.gz from \
		https://www.intel.com/content/www/us/en/developer/articles/tool/simics-simulator.html \
		and store it as $(SIMICS_PKGMGR_DOWNLOAD) or set \
		SIMICS_PKGMGR_DOWNLOAD to its path)

$(SIMICS_ISPM_DOWNLOAD):
	$(error Download simics-6-packages-(version).ispm from \
		https://www.intel.com/content/www/us/en/developer/articles/tool/simics-simulator.html \
		and store it as $(SIMICS_ISPM_DOWNLOAD) or set \
		SIMICS_ISPM_DOWNLOAD to its path)

$(SIMICS_ISPM): $(SIMICS_PKGMGR_DOWNLOAD)
	mkdir -p $(@D)
	tar xf $< -C $(@D) --strip-components=1
	touch $@

$(SIMICS_INSTALL): $(SIMICS_ISPM) $(SIMICS_ISPM_DOWNLOAD)
	$< packages --install-bundle $(SIMICS_ISPM_DOWNLOAD) \
		--install-dir $(SIMICS_INSTALLDIR) --non-interactive
	SIMICS_LATEST=`ls -d $(SIMICS_INSTALLDIR)/simics-?.*/ | tail -n 1`; \
	ln -sf `basename $$SIMICS_LATEST` $(@)


$(SIMICS_PROJECT)/GNUmakefile: $(SIMICS_INSTALL)
	mkdir -p $(SIMICS_PROJECT)
	mkdir -p $(SIMICS_PROJECT)/modules
	ln -rs $(SIMICS_MODULES)/* $(SIMICS_PROJECT)/modules/
	ln -rs $(SIMICS_DIR)/.package-list $(SIMICS_PROJECT)/
	$(SIMICS_BIN)/project-setup --ignore-existing-files $(SIMICS_PROJECT)


$(d)ready: $(SIMICS_PROJECT)/GNUmakefile $(lib_simbricks)
	$(MAKE) -C $(SIMICS_PROJECT) SIMBRICKS_LIB="$(abspath $(lib_dir))"
	touch $@

DISTCLEAN := $(SIMICS_PKGMGR_DOWNLOAD) $(SIMICS_ISPM_DOWNLOAD) \
  $(d)package-manager $(SIMICS_INSTALL) $(SIMICS_INSTALLDIR) \
  $(SIMICS_PROJECT) $(d)ready
include mk/subdir_post.mk

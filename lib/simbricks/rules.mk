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

lib_simbricks := $(lib_dir)libsimbricks.a

libsimbricks_objs :=

$(eval $(call subdir,base))
$(eval $(call subdir,parser))
$(eval $(call subdir,mem))
$(eval $(call subdir,network))
$(eval $(call subdir,pcie))
$(eval $(call subdir,nicif))
$(eval $(call subdir,nicbm))

# --- INSTALLATION TARGETS ---
# Fallback to /usr/local if not set by Conda or Debian
PREFIX ?= /usr/local
DESTDIR ?= 
INCLUDEDIR ?= $(PREFIX)/include
LIBDIR ?= $(PREFIX)/lib/simbricks

$(lib_simbricks): $(libsimbricks_objs)
	$(AR) rcs $@ $(libsimbricks_objs)

install-lib: $(lib_simbricks)
	@echo "Installing SimBricks core libraries to $(DESTDIR)$(PREFIX)..."
	
	# Create the target directories
	install -d $(DESTDIR)$(LIBDIR)
	install -d $(DESTDIR)$(INCLUDEDIR)/simbricks
	
	# Find and copy all compiled static libraries
	find $(lib_dir) -type f -name "*.a" -exec install -m 644 {} $(DESTDIR)$(LIBDIR)/ \;
	
	# Find and copy all C/C++ headers (.h, .hh, .hpp) preserving directory structure
	@for hdr in $$(find $(lib_dir)simbricks -type f \( -name "*.h" -o -name "*.hh" -o -name "*.hpp" \)); do \
		rel_path=$${hdr#$(lib_dir)}; \
		install -D -m 644 $$hdr $(DESTDIR)$(INCLUDEDIR)/$$rel_path; \
	done

pkg_name := simbricks-core-dev
pkg_version := 0.3.6
pkg_arch := amd64
pkg_build_dir := /tmp
pkg := $(pkg_name)_$(pkg_version)_$(pkg_arch)
pkg_dir := $(pkg_build_dir)/$(pkg)
pkg_debian_dir := $(pkg_dir)/DEBIAN
pkg_control_file := $(pkg_debian_dir)/control

lib_pkg := $(lib_dir)$(pkg).deb

$(lib_pkg): $(lib_simbricks)
	@echo "Build SimBricks core lib debian package"

	# Create the base DEBIAN control folder
	mkdir -p $(pkg_debian_dir)

	# Reuse install-lib to populate the package directory
	$(MAKE) install-lib DESTDIR=$(abspath $(pkg_dir)) PREFIX=/usr LIBDIR=/usr/lib/simbricks

	# create control file
	echo "Package: $(pkg_name)" > $(pkg_control_file)
	echo "Version: $(pkg_version)" >> $(pkg_control_file)
	echo "Section: libdevel" >> $(pkg_control_file)
	echo "Priority: optional" >> $(pkg_control_file)
	echo "Architecture: $(pkg_arch)" >> $(pkg_control_file)
	echo "Maintainer: Jakob Görgen jakob@simbricks.io" >> $(pkg_control_file)
	echo "Description: Static core library and headers for SimBricks adapter development" >> $(pkg_control_file)

	# build the package
	dpkg-deb --build $(pkg_dir)
	mv $(pkg_dir).deb $(lib_dir)$(pkg).deb

    # cleanup
	rm -r $(pkg_dir)

	@echo "Finished building debian package"

package: $(lib_pkg)

.PHONY: package install-lib

CLEAN := $(lib_simbricks) $(lib_pkg)
ALL := $(lib_simbricks)
include mk/subdir_post.mk

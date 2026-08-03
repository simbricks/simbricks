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

header_dir := $(CONDA_PREFIX)/include/simbricks

doxygen_outdir := doxygen
doxygen_srcs := $(wildcard $(header_dir)/*/*.h $(header_dir)/*/*.hh $(header_dir)/*/*.hpp)

sphinx_outdir := _build
sphinx_srcs := $(wildcard ./*.rst ./*/*.rst)

documentation: $(doxygen_outdir)/ready $(sphinx_outdir)/ready
.PHONY: documentation

$(doxygen_outdir)/ready: $(d)Doxyfile $(doxygen_srcs)
	cd $(base_dir). && doxygen Doxyfile
	touch $@

$(sphinx_outdir)/ready: $(d)conf.py $(sphinx_srcs)
	cd $(base_dir). && sphinx-build . $(sphinx_outdir)
	touch $@

CLEAN := $(doxygen_outdir) $(sphinx_outdir)

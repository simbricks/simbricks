include mk/subdir_pre.mk

doxygen_outdir := $(d)doxygen
doxygen_srcs := $(wildcard $(d)/*.h)

sphinx_outdir := $(d)_build
sphinx_srcs := $(wildcard $(d)/*.rst $(d)/*/*.rst)

documentation: $(doxygen_outdir) $(sphinx_outdir)
.PHONY: documentation

$(doxygen_outdir): $(d)Doxyfile $(doxygen_srcs)
	cd $(base_dir). && doxygen doc/Doxyfile

$(sphinx_outdir): $(d)conf.py $(sphinx_srcs)
	cd $(base_dir). && sphinx-build doc/ doc/_build

CLEAN := $(doxygen_outdir) $(sphinx_outdir)

include mk/subdir_post.mk

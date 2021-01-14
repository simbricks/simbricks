include mk/subdir_pre.mk
include mk/recipes.mk

base_dir := $(d)./

CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC

VERILATOR = verilator
VFLAGS = +1364-2005ext+v \
    -Wno-WIDTH -Wno-PINMISSING -Wno-LITENDIAN -Wno-IMPLICIT -Wno-SELRANGE \
    -Wno-CASEINCOMPLETE -Wno-UNSIGNED

$(eval $(call subdir,lib))
$(eval $(call subdir,sims))
$(eval $(call subdir,doc))
$(eval $(call subdir,images))


help:
	@echo "Targets:"
	@echo "  all: builds all the tools directly in this repo"
	@echo "  clean: cleans all the tool folders in this repo"
	@echo "  build-images: prepare prereqs for VMs (images directory)"
	@echo "  documentation: build documentation in doc/build_"
	@echo "  external: clone and build our tools in external repos "
	@echo "            (qemu, gem5, ns-3)"

.PHONY: help

include mk/subdir_post.mk

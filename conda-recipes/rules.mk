OUTPUT_FOLDER ?=
OUTPUT_FLAG := $(if $(OUTPUT_FOLDER),--output-folder $(OUTPUT_FOLDER))

BASE_BUILD_CMD := conda build -m conda-recipes/conda_build_config.yaml $(OUTPUT_FLAG)

.PHONY: conda-packages lib dist

conda-packages: lib dist

lib:
	$(BASE_BUILD_CMD) conda-recipes/simbricks-lib

dist: 
	$(BASE_BUILD_CMD) conda-recipes/simbricks-dist

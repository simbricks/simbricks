OUTPUT_FOLDER ?=
OUTPUT_FLAG := $(if $(OUTPUT_FOLDER),--output-folder $(OUTPUT_FOLDER))

BASE_BUILD_CMD := conda build -m conda-recipes/conda_build_config.yaml $(OUTPUT_FLAG)

.PHONY: conda-packages lib dist cli-py client-py local-py orchestration-py \
	runner-py runtime-py telemetry-py utils-py imagebuild-guestfs-py

conda-packages: lib dist cli-py client-py local-py orchestration-py runner-py \
	runtime-py telemetry-py utils-py imagebuild-guestfs-py

lib:
	$(BASE_BUILD_CMD) conda-recipes/simbricks-lib

dist: 
	$(BASE_BUILD_CMD) conda-recipes/simbricks-dist

cli-py: client-py orchestration-py telemetry-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-cli

client-py: orchestration-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-client

local-py: orchestration-py runtime-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-local

orchestration-py: utils-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-orchestration

runner-py: orchestration-py runtime-py client-py telemetry-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-runner

runtime-py: orchestration-py utils-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-runtime

imagebuild-guestfs-py: orchestration-py utils-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-imagebuild-guestfs

telemetry-py: client-py
	$(BASE_BUILD_CMD) conda-recipes/simbricks-telemetry

utils-py:
	$(BASE_BUILD_CMD) conda-recipes/simbricks-utils

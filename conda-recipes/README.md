# SimBricks Conda Recipes

This directory contains the Conda recipes required to build and package various SimBricks components. 

## Structure

* **`conda-recipes/`**: Contains the individual package recipe sub-folders.
* **`conda-recipes/conda_build_config.yaml`**: The configuration file containing variant definitions and build matrices that *must* be passed to the build command.
* **`docker/Dockerfile.conda`**: A Dockerfile based on `condaforge/miniforge3:latest` to spin up a clean environment with all necessary build tools pre-installed.

---

## Environment Setup

You can build these recipes either inside a pre-configured Docker container or directly on your host machine. Only `conda` and `conda-build` are used in this process.

### Method 1: Using Docker

To ensure a clean, isolated environment with all dependencies properly configured, you can use the provided Dockerfile.

1. Build the Docker image from the root of the repository:
   ```bash
   docker build -t simbricks-conda -f docker/Dockerfile.conda .
   ```

2. Run the container interactively:
   ```bash
   docker run -it simbricks-conda
   ```

### Method 2: Local Setup (Without Docker)

If you prefer to build packages on your local system, you only need `conda` and `conda-build` installed. No other tools are required.

1. Install `conda-build` into your active Conda environment:
   ```bash
   conda install conda-build
   ```

---

## Building the Recipes

Run the following commands from the **root** directory of the repository to build the respective packages.

### 1. SimBricks Library (`simbricks-lib`)
```bash
conda build -m conda-recipes/conda_build_config.yaml conda-recipes/simbricks-lib
```

### 2. SimBricks QEMU Simulator (`simbricks-sim-qemu`)
*Note: This depends on `simbricks-lib`, so the local channel `-c local` is included to find the locally built dependency.*
```bash
conda build -c local -m conda-recipes/conda_build_config.yaml conda-recipes/simbricks-sim-qemu
```

### 3. SimBricks i40e BM Simulator (`simbricks-sim-i40e-bm`)
```bash
conda build -c local -m conda-recipes/conda_build_config.yaml conda-recipes/simbricks-sim-i40e-bm
```
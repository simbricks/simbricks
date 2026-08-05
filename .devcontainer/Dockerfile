# SimBricks development container.
#
# One environment that can:
#   - build conda packages           (conda build / make conda-packages)
#   - install SimBricks conda pkgs    (conda install ... from conda.simbricks.io)
#   - compile the C lib and dist      (make lib dist  -> gcc/make + boost + rdma verbs)
#   - develop & test the Python pkgs  (make symphony-dev  -> poetry / pip -e)
#
# miniforge3 (not micromamba like the runtime images) is used because `conda
# build` needs a full conda installation.
FROM condaforge/miniforge3:latest

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential pkg-config make git sudo curl ca-certificates \
      libboost-dev \
      libibverbs-dev librdmacm-dev \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt

ARG CONDA_CHANNEL=latest
RUN conda install -n base -y conda-build poetry \
 && conda config --system --add channels https://conda.simbricks.io/${CONDA_CHANNEL} \
 && conda clean -a -y

ARG USERNAME=simbricks
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
 && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME --shell /bin/bash \
 && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
 && chmod 0440 /etc/sudoers.d/$USERNAME \
 && chown -R $USERNAME:$USERNAME /opt/conda

USER $USERNAME
ENV SB_CONDA_CHANNEL=$CONDA_CHANNEL
RUN conda init bash

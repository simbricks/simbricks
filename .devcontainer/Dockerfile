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
      build-essential \
      pkg-config \
      make \
      git \
      sudo \
      curl \
      ca-certificates \
      libguestfs-tools \
      linux-image-generic \
      libboost-dev \
      libibverbs-dev librdmacm-dev \
 && rm -rf /var/lib/apt/lists/* /var/cache/apt

# libguestfs' 'direct' backend (used by simbricks-imagebuild-guestfs) builds its
# appliance from the kernel linux-image-generic installs and must be able to read
# it as the unprivileged dev user; the distro ships /boot/vmlinuz-* mode 0600.
RUN chmod 0644 /boot/vmlinuz-* 2>/dev/null || true

RUN echo dhcpcd-base | tee -a /usr/lib/*/guestfs/supermin.d/packages

ARG CONDA_CHANNEL=latest
RUN conda install -n base -y conda-build poetry \
 && conda config --system --add channels https://conda.simbricks.io/${CONDA_CHANNEL} \
 && conda clean -a -y

# Reuse the base image's existing unprivileged UID/GID 1000 user ("ubuntu" on
# Ubuntu 24.04): it matches the host user, so it can write the bind-mounted repo,
# and needs no creation. Give it ownership of the conda install so it can install
# packages / run conda build without root.
ARG USERNAME=ubuntu
RUN chown -R $USERNAME:$USERNAME /opt/conda

# The account ships with no password set, so its sudo-group membership is unusable.
# Give it one (same as the username) for occasional `sudo apt update` and the like.
RUN echo "$USERNAME:$USERNAME" | chpasswd

USER $USERNAME
ENV SB_CONDA_CHANNEL=$CONDA_CHANNEL
RUN conda init bash

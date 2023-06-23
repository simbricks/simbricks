<img src="doc/simbricks.svg" alt="SimBricks Logo" width="300" />

# SimBricks

[![CI pipeline status](https://gitlab.mpi-sws.org/simbricks/simbricks/badges/main/pipeline.svg)](https://gitlab.mpi-sws.org/simbricks/simbricks/-/commits/main)
[![Documentation Status](https://readthedocs.org/projects/simbricks/badge/?version=latest)](https://simbricks.readthedocs.io/en/latest/?badge=latest)
[![Docker Hub](https://img.shields.io/badge/docker-hub-brightgreen)](https://hub.docker.com/u/simbricks)
[![Chat on Slack](https://img.shields.io/badge/slack-Chat-brightgreen)](https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA)
[![MIT License](https://img.shields.io/github/license/simbricks/simbricks)](https://github.com/simbricks/simbricks/blob/main/LICENSE.md)

## What is SimBricks?

SimBricks is a simulator framework aiming to enable true end-to-end simulation
of modern data center network systems, including multiple servers running a full
software stack with unmodified OS and applications, network topologies and
devices, as well as other off the shelf and custom hardware components. Instead
of designing a new simulator from scratch, SimBricks combines and connects
multiple existing simulators for different components into a simulated full
system. Our primary use-case for SimBricks is computer systems, networks, and
architecture research. Our [paper](https://arxiv.org/abs/2012.14219) provides a
more detailed discussion of technical details and use-cases.

Currently, SimBricks includes the following simulators:

- [QEMU](https://www.qemu.org) (fast host simulator)
- [gem5](https://www.gem5.org/) (flexible and detailed host simulator)
- [Simics](https://www.intel.com/content/www/us/en/developer/articles/tool/simics-simulator.html)
  (fast, closed-source host simulator supporting modern x86 ISA extensions like
  AVX)
- [ns-3](https://www.nsnam.org/) (flexible simulator for networks)
- [OMNeT++ INET](https://inet.omnetpp.org/) (flexible simulator for networks)
- [Intel Tofino SDK Simulator](https://www.intel.com/content/www/us/en/products/network-io/programmable-ethernet-switch/p4-suite/p4-studio.html)
  (closed-source vendor-provided simulator for Tofino P4 switches).
- [FEMU](https://github.com/ucare-uchicago/FEMU) (NVMe SSD simulator).
- [Verilator](https://www.veripool.org/verilator/) (Verilog RTL simulator)

## Quick Start

Depending on how you plan to use SimBricks, there are different ways to start
using it. The quickest way to get started just running SimBricks is with our
[pre-built Docker container images](https://hub.docker.com/u/simbricks).
However, if you plan to make changes to SimBricks, you will have to build
SimBricks from source, either through Docker, or on your local machine. The
different ways are listed below in order of increasing effort required.

**Please refer to
[our documentation](https://simbricks.readthedocs.io/en/latest/) for more
details.**

### Using Pre-Built Docker Images

**This is the quickest way to get started using SimBricks.**

We provide pre-built Docker images on
[Docker Hub](https://hub.docker.com/u/simbricks). These images allow you to
start using SimBricks without building it yourself or installing any
dependencies. This command will run an interactive shell in a new ephemeral
container (deleted after the shell exits):

```Shell
docker run --rm -it simbricks/simbricks /bin/bash
```

If you are running on a Linux system with KVM support enabled, we recommend
passing `/dev/kvm` into the container to drastically speed up some of the
simulators:

```Shell
docker run --rm -it --device /dev/kvm simbricks/simbricks /bin/bash
```

Finally, some of our host simulators, e.g., gem5 and Simics, require raw
disk images. Since Docker doesn't handle large, sparse files well leading to
large Docker image sizes, we only include disk images in the qcow format. To
convert these to raw, run the following:

```Shell
make convert-images-raw
```

Now you are ready to run your first SimBricks simulation:

```Shell
root@fa76605e3628:/simbricks# cd experiments/
root@fa76605e3628:/simbricks/experiments# simbricks-run --verbose --force pyexps/qemu_i40e_pair.py
...
```

### Experimental: Interactive SimBricks Jupyter Labs

**This is still a work in progress.**

We are working on a more interactive introduction to SimBricks through Jupyter
Labs in [this repository](https://github.com/simbricks/labs). These also simply
require starting a pre-built docker container and then connecting to it from
your browser. After this you can follow the interactive steps to run SimBricks
simulation directly from your browser.

### Building Docker Images

If you prefer to build the Docker images locally you will need `git`, `make`,
and `docker build` installed on your system. Other dependencies should not be
required. Now you are ready to build the docker images (depending on your system
this will likely take 15-45 minutes):

```Shell
git clone https://github.com/simbricks/simbricks.git
cd simbricks
make docker-images
```

This will build a number of Docker images and tag them locally, including the
main `simbricks/simbricks` image.

### Building in VS Code Dev Container

**We recommend this approach if you plan to modify or extend SimBricks.**

This repository is pre-configured with a [Visual Studio Code Development
Container](https://code.visualstudio.com/docs/remote/containers) that includes
all required dependencies for building and working on SimBricks. If you have
Docker set up and the VS Code [Dev Containers
extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
installed, you just have to press `Ctrl+Shift+P` and execute the `Dev Containers: Reopen in
Container` command to open the repository inside the container. This also means
that all VS Code terminals will automatically run any commands inside the
container.

To compile the core SimBricks components simply run `make` (with `-jN` to
use multiple cores). Note that by default, we do not build the Verilator
simulation as these take longer to compile (one to three minutes typically)
and also skip building the RDMA proxy as it depends on the specific RDMA NIC
libraries. These can be enabled by setting `ENABLE_VERILATOR=y ENABLE_RDMA=y`
on the `make` command-line or by creating `mk/local.mk` and inserting those
settings there.

The previous step only builds the simulators directly contained in the SimBricks
repository. You likely also want to build at least some of the external
simulators, such as *gem5*, *QEMU*, or *ns-3*. First, make sure their
corresponding submodules are initialized via `git submodule update --init`. You
can either build all external simulators by running `make -jN external` (this
could take multiple hours depending on your machine), or build them individually
by running e.g. `make -jN sims/external/qemu/ready` (replace `qemu` with `gem5`,
`ns-3`, or `femu` as desired).

Next, to actually run simulations, you also need to build the disk images with
`make -jN build-images` (note this requires QEMU to be built first). This builds
all our disk images, while `make -jN build-images-min` only builds the base disk
image (but not the NOPaxos or Memcached images used for some experiments). This
step will again take 10 - 45 minutes depending on your machine and whether KVM
acceleration is available but only needs to be run once (unless you want to
modify the images).

Now you are ready to run simulations as with the pre-built docker images.

### Building From Source

Finally, it is of course possible to install the required dependencies directly
on your machine and then build and run SimBricks locally. Note that you will
need to install both the build dependencies for SimBricks but also for the
external simulators you need. We suggest you refer to the
[`docker/Dockerfile.buildenv`](docker/Dockerfile.buildenv) for the authoritative
list of required dependencies.

## Questions? Suggestions? Bugs?

If you are using SimBricks or are trying to determine if SimBricks is suitable
for what you are trying to do, we would love to hear from you. First off, please
feel free to report bugs or suggestions directly through [GitHub
issues](https://github.com/simbricks/simbricks/issues). If you have questions or
thoughts, please post them on our [GitHub discussion
board](https://github.com/simbricks/simbricks/discussions). Finally, we are also
available on
[Slack](https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA)
for more interactive discussions or to answer quick questions.

## Repository Structure

- `doc/`: Documentation (Sphinx), automatically deployed on
  [Read The Docs](https://simbricks.readthedocs.io/en/latest/?badge=latest).
- `lib/simbricks/`: Libraries implementing SimBricks interfaces
  - `lib/simbricks/base`: Base protocol implementation responsible for
    connection setup, message transfer, and time synchronization between
    SimBricks component simulators.
  - `lib/simbricks/network`: Network protocol implementation carrying Ethernet
    packets between network components. Layers over the base protocol.
  - `lib/simbricks/pcie`: PCIe protocol implementation, roughly modelling PCIe
    at the transaction level, interconnecting hosts with PCIe device simulators.
    Layers over base protocol.
  - `lib/simbricks/nicbm`: Helper C++ library for implementing behavioral
    (high-level) NIC simulation models, offers similar abstractions as device
    models in other simulators such as gem-5.
  - `lib/simbricks/nicif`: *(deprecated)* Thin C library for NIC simulators
    establishing a network and a PCIe connection.
- `dist/`: Proxies for distributed SimBricks simulations running on multiple
  physical hosts.
  - `dist/sockets/`: Proxy transporting SimBricks messages over regular TCP
    sockets.
  - `dist/rdma/`: RDMA SimBricks proxy (not compiled by default).
- `sims/`: Component Simulators integrated into SimBricks.
  - `sims/external/`: Submodule pointers to repositories for existing external
    simulators (gem5, QEMU, Simics, ns-3, FEMU).
  - `sims/nic/`: NIC simulators
    - `sims/nic/i40e_bm`: Behavioral NIC model for Intel X710 40G NIC.
    - `sims/nic/corundum`: RTL simulation with Verilator of the
      [Corundum FPGA NIC](https://corundum.io/).
    - `sims/nic/corundum_bm`: Simple behavioral Corundum NIC model.
    - `sims/nic/e1000_gem5`: E1000 NIC model extracted from gem5.
  - `sims/net/`: Network simulators
    - `sims/net/net_switch`: Simple behavioral Ethernet switch model.
    - `sims/net/wire`: Simple Ethernet "wire" connecting two NICs back-to-back.
    - `sims/net/pktgen`: Packet generator.
    - `sims/net/tap`: Linux TAP device adapter.
    - `sims/net/tofino/`: Adapter for Intel Tofino Simulator.
    - `sims/net/menshen`: RTL simulation with Verilator for the
      [Menshen RMT Pipeline](https://isolation.quest/).
- `experiments/`: Python orchestration framework for running simulations.
  - `experiments/simbricks/orchestration/`: Orchestration framework implementation.
  - `experiments/run.py`: Main script for running simulation experiments.
  - `experiments/pyexps/`: Example simulation experiments.
- `images/`: Infrastructure to build disk images for host simulators.
  - `images/kernel/`: Slimmed down Linux kernel to reduce simulation time.
  - `images/mqnic/`: Linux driver for Corundum NIC.
  - `images/scripts/`: Scripts for installing packages in disk images.
- `docker/`: Scripts for building SimBricks Docker images.

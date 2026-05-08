# <img src="doc/simbricks-text-horizontal.svg" alt="SimBricks" width="300" />

[![CI pipeline status](https://gitlab.mpi-sws.org/simbricks/simbricks/badges/main/pipeline.svg)](https://gitlab.mpi-sws.org/simbricks/simbricks/-/commits/main)
[![Documentation Status](https://readthedocs.org/projects/simbricks/badge/?version=latest)](https://simbricks.readthedocs.io/en/latest/?badge=latest)
[![Docker Hub](https://img.shields.io/badge/docker-hub-brightgreen)](https://hub.docker.com/u/simbricks)
[![Chat on Slack](https://img.shields.io/badge/slack-Chat-brightgreen)](https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA)
[![MIT License](https://img.shields.io/github/license/simbricks/simbricks)](https://github.com/simbricks/simbricks/blob/main/LICENSE.md)

## What is SimBricks?

SimBricks is an open-source simulation framework for intricate HW-SW systems
that enables rapid virtual prototyping and meaningful end-to-end evaluation in
simulation. SimBricks modularly combines and connects battle-tested simulators
for different components: machines (e.g. QEMU, gem5, Simics), hardware
components (e.g. Verilator, Tofino, FEMU SSD), and networks (e.g. ns-3,
OMNeT++). SimBricks simulations run unmodified full-system stacks, including
applications, operating systems such as Linux, and hardware RTL.

## Getting started with SimBricks

Please **refer to [our documentation](https://simbricks.readthedocs.io/en/latest/)
that explaines the easiest way to [get started](https://simbricks.readthedocs.io/en/latest/quickstart/index.html)
using SimBricks**. Besides, our documentation goes into more detail on how
SimBricks works, is used and can be extended.

## Questions? Suggestions? Bugs?

If you are using SimBricks or are trying to determine if SimBricks is suitable
for what you are trying to do, we would love to hear from you. First off, please
feel free to report bugs or suggestions directly through [GitHub
issues](https://github.com/simbricks/simbricks/issues). If you have questions or
thoughts, please post them on our [GitHub discussion
board](https://github.com/simbricks/simbricks/discussions) or reach out to us
via [email](mailto:team@simbricks.io). Finally, we are also available on
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
  - `lib/simbricks/mem`: Simplified memory protocol impementation.
  - `lib/simbricks/parser`: Library implementing SimBRicks parameter parsing and
    interface establishment to ease writing SimBricks adapters.
  - `lib/simbricks/axi`: Helper C++ library for implementing AXI-Light and 
    AXI-Stream interfaces in a SimBricks adapter.to 
- `dist/`: Proxies for distributed SimBricks simulations running on multiple
  physical hosts.
  - `dist/sockets/`: Proxy transporting SimBricks messages over regular TCP
    sockets.
  - `dist/rdma/`: RDMA SimBricks proxy (not compiled by default).
- `sims/`: Component Simulators integrated into SimBricks. Note however that not
  all integrated simulators are part of the main repo (e.g. Corundum that you
  can find in our [examples repo](https://github.com/simbricks/simbricks-examples))
  - `sims/external/`: Submodule pointers to repositories for existing external
    simulators (gem5, QEMU, Simics, ns-3, FEMU).
  - `sims/nic/`: NIC simulators
    - `sims/nic/i40e_bm`: Behavioral NIC model for Intel X710 40G NIC.
    - `sims/nic/e1000_gem5`: E1000 NIC model extracted from gem5.
  - `sims/net/`: Network simulators
    - `sims/net/switch`: Simple behavioral Ethernet switch model.
    - `sims/net/wire`: Simple Ethernet "wire" connecting two NICs back-to-back.
    - `sims/net/pktgen`: Packet generator.
    - `sims/net/tap`: Linux TAP device adapter.
    - `sims/net/tofino/`: Adapter for Intel Tofino Simulator.
    - `sims/net/menshen`: RTL simulation with Verilator for the
      [Menshen RMT Pipeline](https://isolation.quest/).
- `experiments/`: Simple example virtual prototypes using SimBricks orchestration
  framework. For more exampels look in our [examples repo](https://github.com/simbricks/simbricks-examples).
- `symphony`: SimBricks Python packages to generally use and interact with SimBricks.
  - `symphony/orchestration`: Python package to configure virtual prototypes.
  - `symphony/cli`: SimBricks cli interface to interact with SimBricks.
  - `symphony/client`: SimBricks client to connect to SimBricks cloud version.
  - `symphony/runtime`: SimBricks runtime managing simulator lifecycle durign
    execturion.
  - `symphony/runner`: SimBricks runner for using SimBricks cloud version.
- `images/`: Infrastructure to build disk images for host simulators.
  - `images/kernel/`: Slimmed down Linux kernel to reduce simulation time.
  - `images/mqnic/`: Linux driver for Corundum NIC.
  - `images/scripts/`: Scripts for installing packages in disk images.
- `docker/`: Scripts for building SimBricks Docker images.

..
  Copyright 2026 Max Planck Institute for Software Systems,
  National University of Singapore, and SimBricks UG (haftungsbeschraenkt)
..
  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:
..
  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.
..
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

.. _sec-conda-packages:

Installing SimBricks Packages (Conda Channel)
*********************************************

All SimBricks components — the core libraries, the Python orchestration packages, and every
integrated simulator — are distributed as conda packages through the SimBricks conda channel.
The Python packages are additionally published to PyPI on releases, so for *writing* virtual
prototypes and talking to the SimBricks Cloud, plain ``pip install`` works too (that is what the
:ref:`Quickstart <chap-quickstart-sec-setup>` uses). The conda channel is the way to get the
**simulator binaries**, which are not pip-installable.

.. _sec-conda-channels:

Channels: stable vs. latest
===========================

The channel comes in two variants:

- ``https://conda.simbricks.io/stable`` — built from the ``release`` branches. This is the
  channel to use for regular work: SimBricks releases are built against it, and it only moves
  when a new version is released.
- ``https://conda.simbricks.io/latest`` — built continuously from the ``main`` branches. Use it
  during development to preview the upcoming, not-yet-released state of SimBricks — for example
  to check how your virtual prototypes or simulator integrations behave against what will become
  the next release. Everything in ``latest`` eventually lands in ``stable`` with the next
  release.

Do not mix the two channels within one environment — the package versions are pinned against each
other, so a mixed environment can end up inconsistent. To try ``latest``, simply create a second
environment that uses ``latest`` in place of ``stable`` in the commands below, and switch between
the environments with ``micromamba activate``.

Setup
=====

Any conda-compatible package manager works; we recommend :micromamba:`\ `:

.. code-block:: bash

  # install micromamba (see the micromamba docs for details)
  "${SHELL}" <(curl -L micro.mamba.pm/install.sh)

  # register the SimBricks channel (swap stable for latest to preview development builds)
  micromamba config append channels https://conda.simbricks.io/stable
  micromamba config append channels conda-forge

Then install what you need, e.g.:

.. code-block:: bash

  # authoring + cloud submission only (pure Python)
  micromamba install simbricks-orchestration simbricks-client simbricks-cli

  # local execution of the quickstart example: local runtime + simulators
  micromamba install simbricks-local simbricks-qemu-sim-bin \
      simbricks-i40e-sim-bm-bin simbricks-net-base-sim-bin

Note that installing a simulator's ``*-bin`` package automatically pulls in the matching Python
integration packages, so the simulator is immediately usable from virtual prototype scripts.

.. note::
  The binary packages are currently built for ``linux-64`` only. On other platforms, use the
  :ref:`Docker images <sec-docker-images>`.

Package inventory
=================

**Core packages** (from :simbricks-repo-plain:`simbricks/simbricks <>`):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Contents
   * - ``simbricks-lib``
     - SimBricks protocol libraries and headers (C/C++), needed to build adapters/simulators
   * - ``simbricks-dist``
     - Proxies for distributed simulation (``net_sockets``, ``net_rdma``)
   * - ``simbricks-utils``
     - Shared Python utilities (``simbricks.utils``)
   * - ``simbricks-orchestration``
     - The orchestration framework (``simbricks.orchestration``)
   * - ``simbricks-runtime``
     - Runtime managing simulator lifecycle during execution (``simbricks.runtime``)
   * - ``simbricks-client``
     - Client library for the SimBricks Backend (``simbricks.client``)
   * - ``simbricks-telemetry``
     - Telemetry support (``simbricks.telemetry``)
   * - ``simbricks-cli``
     - The ``simbricks-cli`` command-line tool
   * - ``simbricks-runner``
     - The Runner (``simbricks-runner`` and ``simbricks-executor-local`` commands)
   * - ``simbricks-local``
     - Local execution without cloud (``simbricks-run`` command)

**Component packages** (one set per ``component-*`` repository): the naming scheme is
``simbricks-<x>-sys-py`` for system components, ``simbricks-<x>-sim[-<flavor>]-py`` for the
simulator classes, and ``simbricks-<x>-sim[-<flavor>]-bin`` for the executable (flavors: ``bm`` =
behavioral model, ``rtl`` = RTL simulation). See the table in :ref:`the simulator overview
<chap-quickstart>` on the landing page for the full list; the executables provided are:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Binary package
     - Executable(s)
     - Python simulator class(es)
   * - ``simbricks-qemu-sim-bin``
     - ``qemu-system-x86_64``, ``qemu-img``
     - ``QemuSim``
   * - ``simbricks-gem5-sim-bin``
     - ``$CONDA_PREFIX/opt/gem5/build/X86/gem5.fast`` (+ config scripts)
     - ``Gem5Sim``
   * - ``simbricks-ns3-sim-bin``
     - ``simbricks-ns3-net``, ``simbricks-ns3-dumbbell``, ``simbricks-ns3-bridge``
     - ``NS3Net``, ``NS3DumbbellNet``, ``NS3BridgeNet``
   * - ``simbricks-net-base-sim-bin``
     - ``simb_net_switch``, ``simb_net_wire``, ``simb_net_tap``, ``simb_net_pktgen``
     - ``SwitchNet``, ``WireNet``
   * - ``simbricks-mem-base-sim-bin``
     - ``simb_mem_basicmem``, ``simb_mem_interconnect``, ``simb_mem_terminal``
     - ``BasicMem``, ``BasicInterconnect``, ``MemTerminal``
   * - ``simbricks-i40e-sim-bm-bin``
     - ``simb_i40e_bm``
     - ``I40eNicSim``
   * - ``simbricks-e1000-sim-bm-bin``
     - ``simb_e1000_gem5``
     - ``E1000NIC``
   * - ``simbricks-corundum-sim-rtl-bin``
     - ``simb_corundum``
     - ``CorundumVerilatorNICSim``
   * - ``simbricks-femu-sim-bin``
     - ``femu-simbricks``
     - ``FEMUSim``

.. note::
  gem5 is the one simulator not resolved via ``$PATH``: ``Gem5Sim`` locates the binary and config
  scripts under ``$CONDA_PREFIX/opt/gem5/``. For a local, non-conda gem5 build, point the
  ``GEM5_PREFIX`` environment variable at your build tree instead.

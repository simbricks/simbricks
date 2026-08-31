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

.. _sec-simulator-integration-packaging:

Packaging a Simulator as a Component Repository
===============================================

In the modular SimBricks layout, every simulator integration lives in its own *component
repository* under the SimBricks GitHub organization (``component-<x>``) and is distributed as a
set of conda packages through the SimBricks conda channel. This page describes the pattern, so
you can follow it for your own simulator — whether you publish it publicly or keep it internal.

.. tip::
  The best reference implementations are :component-corundum:`\ ` (RTL simulator via Verilator,
  including a guest driver), :component-qemu:`\ ` (large external simulator integrated via a
  fork + submodule), and :component-i40e:`\ ` (self-contained behavioral model). Have a look at
  their READMEs and copy liberally.

Repository layout
-----------------

Component repositories all follow the same skeleton:

.. code-block:: text

  component-<x>/
    .github/workflows/conda-packages.yml   # thin caller of the shared CI workflow
    conda-recipes/
      conda_build_config.yaml              # version pin for all packages in this repo
      simbricks-<x>-...-bin/               # recipe for the binary package
        build.sh
        meta.yaml
      simbricks-<x>-...-py/meta.yaml       # recipe(s) for the Python package(s)
    <src>/                                 # simulator/adapter sources, or a git submodule
    <x>_sys_py/simbricks/components/<x>/system/...        # optional system components
    <x>_sim_py/simbricks/components/<x>/simulation/...    # simulator class(es)
    Makefile                               # local dev build + conda-packages + pypi targets
    LICENSE, README.md

For simulators with a large existing code base (QEMU, gem5, ns-3, FEMU), the simulator itself is a
**git submodule pointing to a SimBricks fork** that carries the Adapter (e.g.
:qemu-fork:`simbricks/qemu <>`, :gem5-fork:`simbricks/gem5 <>`, :ns3-fork:`simbricks/ns-3 <>`).
For self-contained models (i40e, e1000, the basic net/mem simulators), the sources live directly
in the repository.

The package triple
------------------

A full integration produces up to three kinds of packages (see also
:ref:`sec-orchestration-framework-components`):

1. ``simbricks-<x>-sys-py`` — *system components* (noarch Python). Depends only on
   ``simbricks-orchestration``. Only needed when the component introduces new system classes
   (e.g. a NIC model plus a host class that loads its driver). Simulators that only simulate
   existing generic components (e.g. QEMU simulating a generic Linux host) don't need one.
2. ``simbricks-<x>-sim[-<flavor>]-py`` — the *simulator class* (noarch Python). Depends on
   ``simbricks-orchestration`` (and, if present, pins the co-built ``-sys-py`` package with
   ``==``). The flavor distinguishes multiple simulators for the same component: ``bm`` for a
   behavioral model, ``rtl`` for RTL simulation via Verilator.
3. ``simbricks-<x>-sim[-<flavor>]-bin`` — the *compiled simulator binary* (linux-64). Built
   against the ``simbricks-lib`` package (the SimBricks protocol libraries and headers) and
   installed into ``$PREFIX/bin``. Crucially, its ``run:`` dependencies pin the sibling Python
   package(s) with ``==`` — so ``micromamba install simbricks-corundum-sim-rtl-bin`` pulls in the
   orchestration glue automatically, and a Runner that installs the binary is immediately able to
   execute virtual prototypes using it.

**The executable-name contract.** The binary package installs the simulator executable under
exactly the name that the simulator class passes as ``executable=`` (e.g. ``simb_corundum`` ↔
``CorundumVerilatorNICSim``, ``simb_i40e_bm`` ↔ ``I40eNicSim``, ``simb_net_switch`` ↔
``SwitchNet``). Resolution happens purely through ``$PATH`` — there is no registry. By convention,
SimBricks-specific binaries are prefixed with ``simb_``.

The Python packages use implicit namespace packaging: the ``simbricks/`` and
``simbricks/components/`` directories contain **no** ``__init__.py``, only the leaf package does.
This is what lets independently installed component packages merge into the single
``simbricks.components.*`` import tree. The ``pyproject.toml`` uses poetry-core, e.g.:

.. code-block:: toml

  [build-system]
  requires = ["poetry-core>=1.0.0"]
  build-backend = "poetry.core.masonry.api"

  [tool.poetry]
  name = "simbricks-i40e-sys-py"
  version = "0.5.0"
  packages = [ { include = "simbricks" } ]

  [tool.poetry.dependencies]
  simbricks-orchestration = ">=0.5.0"

Versioning
----------

Each repository's ``conda-recipes/conda_build_config.yaml`` holds ``simbricks_version`` as the
single source of truth for the versions of all packages built from that repository, and drives the
``==`` pins between them. It must be kept in sync by hand with the ``version`` fields in the
``pyproject.toml`` files. Dependencies on packages from *other* repositories (``simbricks-lib``,
``simbricks-orchestration``, ``simbricks-utils``) use independent ``>=`` bounds.

Building and publishing
-----------------------

Each repository's ``Makefile`` provides a uniform set of targets:

- ``make conda-packages`` — build all conda packages of the repo with ``conda build``, resolving
  external SimBricks dependencies from the public channel
  (``-c https://conda.simbricks.io/latest``). Development builds resolve against ``latest``;
  release builds are made against ``stable``. Build the recipes sequentially (do not pass
  ``-j``), so each build finds the packages produced by the previous one in the local channel.
- ``make <x>-build`` / ``make <x>-install`` — build/install the simulator binary directly, for
  local development without going through conda packaging. Point the build at your installed
  SimBricks headers/libraries, e.g.
  ``make <x>-build SIMBRICKS_INC_DIR="$CONDA_PREFIX/include" SIMBRICKS_LIB_DIR="$CONDA_PREFIX/lib"``.
- ``make python-develop`` (or ``<x>-python-develop``) — editable ``pip install -e`` of the Python
  package(s) for iterating on the orchestration glue.
- ``make pypi-build`` / ``make pypi-publish`` — build/publish the Python packages to PyPI via
  poetry (releases only).

Continuous integration is shared: every component repository's
``.github/workflows/conda-packages.yml`` is a six-line caller of the reusable workflow in
:ci-workflows:`\ `, which builds the packages in the SimBricks conda build container and uploads
them to the channel — pushes to ``main`` publish to the ``latest`` channel, pushes to ``release``
publish to ``stable`` (and additionally publish the Python packages to PyPI).

Guest-side pieces (drivers, tools)
----------------------------------

Some integrations also need software *inside* the simulated machine — e.g. the Corundum ``mqnic``
kernel driver, or gem5's ``m5`` guest tool. These are **not** conda packages: they must be baked
into the disk image the virtual prototype boots. The convention is that the component repository
provides Makefile targets for building/installing them in-guest (e.g. ``make driver-install``),
and that a virtual prototype can install them into the image it boots — either as a layer on a
layered image (see :ref:`sec-disk-images-building`) or baked into a base image built with
:image-builder:`\ `, whose ``examples/corundum/install-mqnic.sh`` and ``examples/gem5/install-m5.sh``
show the shape of such a script. The pre-built ``base`` image already contains the mqnic driver
and the m5 tool.

Making a simulator available on Runners
---------------------------------------

Because the binary package carries its Python glue as a dependency, provisioning a Runner for your
simulator is a one-liner in its environment: ``micromamba install simbricks-<x>-...-bin``. For the
standard set of simulators, the pre-built ``simbricks/simbricks-executor`` Docker image already
includes everything (see :ref:`sec-docker-images`). For custom simulators, install your package
into the Runner's environment — or run a dedicated fragment executor for it and select it from
your scripts with ``fragment.fragment_executor_tag`` (see :ref:`sec-runner`).

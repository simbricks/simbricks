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

.. _sec-bare-metal:

Building From Source (Bare Metal)
*********************************

For working on the SimBricks core itself — the protocol libraries, the proxies, or the Python
orchestration packages — you build directly from the main repository:

.. code-block:: bash

  git clone https://github.com/simbricks/simbricks.git
  cd simbricks

C/C++ parts
===========

``make`` builds the components contained in the repository: the SimBricks protocol libraries
(``lib/``, producing ``libsimbricks.a`` and the per-protocol archives) and the distributed-
simulation proxies (``dist/sockets/net_sockets``; add ``ENABLE_RDMA=y`` in ``mk/local.mk`` or on
the command line to also build ``dist/rdma/net_rdma``, which requires ``rdma-core``).

You need a C/C++ toolchain (gcc/g++), GNU make, and boost. For the authoritative dependency set,
consult the conda recipes in ``conda-recipes/`` (``simbricks-lib``, ``simbricks-dist``) — they are
what CI builds with. Alternatively, develop inside the ``simbricks/simbricks-baseenv`` container
and install the toolchain from conda.

``make install-lib`` / ``make install-dist`` install libraries, headers, and proxies to a prefix;
see :ref:`sec-deb-package` for building a Debian package of the core library instead.

Simulators are **not** part of this repository: each lives in its own ``component-*`` repository
and is built there against an installed ``simbricks-lib`` (see
:ref:`sec-simulator-integration-packaging`).

Python packages (symphony)
==========================

The Python packages all live under ``symphony/``. For development, install them editable into your
current environment (virtualenv or conda environment, Python >= 3.10):

.. code-block:: bash

  make symphony-dev

This installs ``simbricks-utils``, ``simbricks-orchestration``, ``simbricks-runtime``,
``simbricks-client``, ``simbricks-telemetry``, ``simbricks-cli``, ``simbricks-runner``, and
``simbricks-local`` with ``pip install -e``, so your changes are picked up immediately. Type
checking runs with ``make symphony-typecheck``.

Conda packages
==============

The conda recipes for everything in this repository are under ``conda-recipes/`` and build with
``make conda-packages`` (requires ``conda-build``; the recipes resolve their dependencies from the
public SimBricks channel).

Documentation
=============

The build dependencies of this documentation (sphinx, doxygen, and the SimBricks packages that
are autodoc'ed in the reference) are installed as conda packages from ``doc/environment.yml``:

.. code-block:: bash

  micromamba env create -f doc/environment.yml
  micromamba activate simbricks-docs
  make documentation

The result lands in ``doc/_build``. The checked-in environment resolves the SimBricks packages
from the ``stable`` channel — the same channel released documentation is built against on
readthedocs. To check how the documentation looks against the upcoming, not-yet-released state,
create the environment from the ``latest`` channel instead by swapping the channel URL in
``doc/environment.yml`` (see the comment there), e.g.:

.. code-block:: bash

  sed 's|conda.simbricks.io/stable|conda.simbricks.io/latest|' doc/environment.yml \
      | micromamba env create -n simbricks-docs-latest -f /dev/stdin
  micromamba activate simbricks-docs-latest
  make documentation

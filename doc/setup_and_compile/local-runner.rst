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

.. _sec-local-runner:

Running Your Own Runner
***********************

To execute virtual prototypes on your own machines while still using the SimBricks Cloud for
management and scheduling, you set up your own :ref:`Runners <sec-runner>`. A Runner registers
itself with the Backend under your namespace; the Backend then schedules matching Runs onto it.

Register the Runner
===================

First, create the Runner on the Backend to obtain its id, e.g. via the CLI (see
:ref:`sec-cli-ref`):

.. code-block:: bash

  simbricks-cli runners create <resource_group_id> <label> [<tags>...]

The tags you assign here are matched against the ``runner_tags`` of submitted Fragments.

Option 1: Docker (recommended)
==============================

The easiest way to run a Runner is the pre-built image (see :ref:`sec-docker-images`). The
entrypoint expects your namespace and the runner id as arguments:

.. code-block:: bash

  docker run --rm -it --device /dev/kvm \
      -v /var/run/docker.sock:/var/run/docker.sock \
      simbricks/simbricks-runner <NAMESPACE> <RUNNER_ID>

By default the Runner is configured with a single *local* fragment executor (executing simulations
in the Runner's own environment). To have the Runner spawn executions in
``simbricks/simbricks-executor`` containers instead, configure the Docker plugin (below).

Option 2: Bare metal
====================

Install the runner package and the simulators you want to offer from the conda channel:

.. code-block:: bash

  micromamba install simbricks-runner simbricks-qemu-sim-bin ...  # etc.
  simbricks-runner --configuration_file runner_config.yaml

The Runner reads its settings from environment variables / a ``runner.env`` file (namespace,
runner id, backend URL — the defaults point to ``https://app.simbricks.io/api``) and its fragment
executors from a YAML configuration file.

Fragment executor configuration
===============================

The configuration file declares which fragment executors the Runner offers. Each entry has a tag
(selectable from scripts via ``fragment.fragment_executor_tag``) and a plugin:

.. code-block:: yaml

  fragment_executors:
    - base_executor:
        plugin: simbricks.runner.main_runner.plugins.local_plugin
    - corundum_executor:
        plugin: simbricks.runner.main_runner.plugins.docker_plugin
        docker_image: "my-registry/my-corundum-executor"
        docker_pull: true

- The **local plugin** spawns ``simbricks-executor-local`` directly in the Runner's environment —
  all simulators of the fragment must be installed there.
- The **docker plugin** spawns the fragment inside a container (default image
  ``simbricks/simbricks-executor``); images can be restricted via allow/deny lists and extended
  with additional ``docker_opts``. The container is started with ``--device=/dev/kvm``, so the
  host needs KVM access for fast QEMU runs.

Hardware/OS requirements are the same as for the executor image (see :ref:`sec-docker-images`):
``/dev/kvm`` for QEMU, ``kernel.perf_event_paranoid <= 1`` for gem5, and disk images available
under the global input directory (pre-installed in the executor image; for bare-metal setups,
provide them yourself and set ``GLOBAL_INPUT_DIR`` — see :ref:`sec-disk-images-global-input`).

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

.. _sec-docker-images:

Using Pre-Built Docker Images
*****************************

SimBricks provides pre-built Docker images on :docker-hub:`\ `. Since the move to conda packaging,
there are exactly **three** images, building on each other:

- ``simbricks/simbricks-baseenv`` — Ubuntu base environment with :micromamba:`\ ` installed and
  the SimBricks conda channel pre-configured. Use this as a starting point for custom environments:
  any SimBricks package is a ``micromamba install`` away.
- ``simbricks/simbricks-runner`` — base environment plus the ``simbricks-runner`` package. Runs a
  :ref:`Main Runner <sec-runner>` that connects to the SimBricks Backend
  (entrypoint ``run_runner.sh``, see :ref:`sec-local-runner`).
- ``simbricks/simbricks-executor`` — runner image plus the standard simulator packages
  (QEMU, gem5, ns-3, FEMU, i40e, e1000, and the basic net/mem simulators) **and** a pre-built
  ``base`` disk image at ``/global_input/images/base/`` (built with :image-builder:`\ `, including
  the gem5-compatible kernel, the ``m5`` tool, and the Corundum ``mqnic`` driver). This is the
  image that actually executes simulations, either spawned by a Runner's Docker plugin or used
  directly.

For a quick interactive environment with all standard simulators available, you can enter the
executor image directly:

.. code-block:: bash

  docker run --rm -it --device /dev/kvm --entrypoint /bin/bash simbricks/simbricks-executor

Requirements on the host
========================

**KVM for fast QEMU simulations.** For QEMU's fast functional mode, the container needs access to
the KVM device, enabled with ``--device /dev/kvm`` (check that ``/dev/kvm`` exists on your host —
on machines without virtualization support or VMs without nested virtualization you can still run
QEMU, just slower via TCG).

**perf event access for gem5.** gem5 requires the Linux ``perf_event_paranoid`` setting to be 1 or
lower. Since this is a kernel setting, it can only be changed from a privileged container (or
directly on the host):

.. code-block:: bash

  docker run --rm -it --device /dev/kvm --privileged --entrypoint /bin/bash simbricks/simbricks-executor
  # inside the container:
  sudo sysctl -w kernel.perf_event_paranoid=1

**Raw images for gem5.** The shipped ``base`` image is in qcow2 format. gem5 requires raw images;
the executor's default entrypoint converts the image on startup, but when entering the container
manually you can convert it yourself:

.. code-block:: bash

  qemu-img convert -f qcow2 -O raw -S 4k \
      /global_input/images/base/base /global_input/images/base/base.raw

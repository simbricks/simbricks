..
  Copyright 2021 Max Planck Institute for Software Systems, and
  National University of Singapore
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

Using Pre-Built Docker Images
=============================

We provide pre-built Docker images on :docker-hub:`\ `.
These images provide a ready-to-use environment without building it yourself,
containing all necessary dependencies to build custom disk images, compile
adapters, or execute specialized workloads like self-hosted runners.

To start an interactive shell in a new ephemeral container (which will be
deleted after the shell exits), use the following command:

.. code-block:: bash

   docker run --rm -it --device /dev/kvm --privileged simbricks/simbricks-local /bin/bash

**Performance & Requirements:**
If your host system or runner node has Linux KVM support enabled, we highly
recommend passing ``/dev/kvm`` into the container. This drastically speeds up
some of the simulators. It is even required for certain simulators like gem5.

Furthermore, if your workload involves gem5, the container must be started with
the ``--privileged`` flag since it must access the ``perf_event_open`` syscall.
In addition, you must also set ``/proc/sys/kernel/perf_event_paranoid`` to ``1``
or lower on the host machine. You can set this temporarily by running the
following command:

.. code-block:: bash

   sudo sysctl -w kernel.perf_event_paranoid=1

**Image Format Conversion:**
Certain host simulators, e.g. gem5 or Simics, require raw disk images. Because
Docker does not efficiently handle large, sparse files that lead to huge Docker
image sizes, we ship our images in ``qcow`` format to minimize image size. If
your workflow requires raw images, you can convert them by running the following
command inside the container:

.. code-block:: bash

   make convert-images-raw
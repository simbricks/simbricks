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

.. _sec-build-docker:

Building Docker Images Locally
******************************

If you want to modify the SimBricks Docker images — for example, to bake additional simulators or
custom disk images into an executor — you can build them locally from the main repository:

.. code-block:: bash

  git clone https://github.com/simbricks/simbricks.git
  cd simbricks
  make docker-images

This builds and locally tags the three images ``simbricks/simbricks-baseenv``,
``simbricks/simbricks-runner``, and ``simbricks/simbricks-executor`` (see :ref:`sec-docker-images`
for what each contains). The corresponding Dockerfiles live in ``docker/``.

A few knobs are configurable via make variables (see ``docker/rules.mk``): ``DOCKER_REGISTRY``
and ``DOCKER_TAG`` for naming, and ``CONDA_CHANNEL`` to build against the ``latest`` (default) or
``stable`` SimBricks conda channel.

.. note::
  Building the executor image takes a while (typically well over 30 minutes): it clones the
  :image-builder:`\ ` repository, builds the gem5-compatible kernel, and builds the complete
  ``base`` disk image inside the Docker build (using TCG, since KVM is not available there).

For custom executor environments it is usually easier to *extend* the pre-built images than to
rebuild them, e.g.:

.. code-block:: docker

  FROM simbricks/simbricks-executor
  RUN micromamba install -y simbricks-my-simulator-sim-bin
  COPY my-image/ /global_input/images/my-image/

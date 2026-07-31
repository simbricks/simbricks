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

.. _sec-disk-images:

Disk Images and Data Flow
**********************************************

Full-system host simulators such as QEMU and gem5 boot a complete Linux system. For this they need
a disk image containing the operating system, drivers, and benchmark applications, plus the boot
artifacts (kernel, initrd). This chapter explains how disk images are referenced in virtual
prototype scripts, where the files come from, and how per-run inputs and outputs flow through a
simulation.

Disk images in the System Configuration
=======================================

Disk images are part of the System Configuration. ``simbricks.orchestration.system`` provides a
small hierarchy of disk image classes (see :ref:`sec-orchestration-framework-ref` for the API
reference). A disk image is created once on the ``System`` and can then be attached to one or more
hosts with ``host.add_disk()``:

.. code-block:: python

  from simbricks.orchestration import system

  syst = system.System()
  disk = system.DistroDiskImage(syst, "base")

  host0 = ...
  host0.add_disk(disk)
  host0.add_disk(system.LinuxConfigDiskImage(syst, host0))

The available disk image types are:

- ``DistroDiskImage(system, name)``: references one of the disk images distributed alongside
  SimBricks **by name**. At execution time, the image is looked up in the *global input directory*
  of the execution environment under ``images/<name>/<name>`` (qcow2) or
  ``images/<name>/<name>.raw`` (raw) — see below. The ``base`` image built by the
  :image-builder:`\ ` tool is pre-installed in the SimBricks executor environments.
- ``ExternalDiskImage(system, path)``: references a raw/qcow2 image you built yourself via an
  explicit path.
- ``LinuxConfigDiskImage(system, host)``: a small, dynamically generated image containing the
  commands to run on the host during simulation (generated from the host's applications and
  configuration). This is how your workload gets into the guest — see
  :ref:`sec-disk-images-guest-payload`.
- ``PackerDiskImage(system, packer_config_path)``: builds a custom image with
  :packer:`\ ` as part of preparing the simulation, using an image-builder-style Packer
  configuration.
- ``DummyDiskImage``: placeholder for hosts that do not need an actual image.

Different host simulators support different image formats: QEMU works with qcow2 (using a
copy-on-write overlay per host, so hosts can share one backing image) and raw, while gem5 requires
raw images. The orchestration framework automatically selects a format both the image and the
simulator support, and copies the image per host where necessary.

.. _sec-disk-images-global-input:

The global input directory
==========================

Executions resolve ``DistroDiskImage`` references inside a **global input directory**: a directory
of (typically large, reusable) input files that exists once per execution environment rather than
per run. The expected layout for disk images is:

.. code-block:: text

  <global_input>/images/<name>/<name>        # the image, qcow2
  <global_input>/images/<name>/<name>.raw    # the image, raw (needed by gem5)
  <global_input>/images/<name>/boot/vmlinuz  # kernel (bzImage), used by QEMU
  <global_input>/images/<name>/boot/initrd   # initramfs, used by QEMU
  <global_input>/images/<name>/boot/vmlinux  # kernel (ELF), used by gem5

This is exactly the output layout that the :image-builder:`\ ` tool produces (its
``output/<name>/`` directory), so populating a global input directory amounts to copying image
builder outputs there. See :ref:`sec-image-builder` for how to build the ``base`` image and custom
variants.

How the global input directory is located depends on how you execute:

- **SimBricks Cloud / executor image:** the ``simbricks/simbricks-executor`` Docker image ships
  with a pre-built ``base`` image at ``/global_input/images/base/`` and sets the
  ``GLOBAL_INPUT_DIR=/global_input`` environment variable.
- **Local execution with** ``simbricks-run``: pass ``--global-input-dir <DIR>`` on the command
  line (see :ref:`sec-execution`).

At preparation time, the global input directory is symlinked into the run's working directory as
``global_input``, and simulators resolve boot artifacts through that link (e.g. QEMU passes
``global_input/images/base/boot/vmlinuz`` as its kernel).

.. _sec-disk-images-guest-payload:

Getting your workload into the guest
====================================

The commands that a host executes during simulation are configured through its applications
(``host.add_app(...)``). Under the hood, ``LinuxConfigDiskImage`` packs the generated commands
(``guest/run.sh``, plus any additional config files you attach to the host) into a tar archive that
is attached to the simulated host as a second disk. The disk images built by image-builder install
a small init script (``guestinit.sh``) in the guest that unpacks this archive from ``/dev/sdb``
and executes ``guest/run.sh``. The host simulator's kernel command line is set up to run this init
script instead of a regular init system, and all output is delivered over the serial console
``ttyS0``, which is how the application output ends up in your simulation logs.

This means: to run your own software in the guest, you either add it as commands/applications in
the System Configuration (for anything that can be installed/executed at runtime) or bake it into
a custom disk image with image-builder (for drivers, kernel modules, or large installations) — see
:ref:`sec-image-builder`.

Run working directory and outputs
=================================

Each run executes in its own working directory with a fixed layout, managed by the orchestration
framework's ``InstantiationEnvironment``:

.. code-block:: text

  <workdir>/
    global_input -> <global input directory>   # symlink, if configured
    input_artifacts/                           # unpacked input artifacts
    tmp/
      imgs/                # per-host image copies/overlays and generated config images
      checkpoints/         # simulator checkpoints (if enabled)
      shm/                 # shared-memory queues connecting the simulators
      proxies/             # proxy state for distributed runs
    output/
      output.<simulator>-<id>/   # per-simulator output directories
      out.json                   # collected output of the whole simulation

After a run completes, the collected simulator output is available as JSON (``output/out.json``).
When running through the SimBricks Cloud, this output is what the Backend stores and what the CLI
and client library retrieve; additionally, Fragments can declare *output artifacts* (files to
collect after execution) and *input artifacts* (files to ship to the Runner before execution).

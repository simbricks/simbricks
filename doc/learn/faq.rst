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

.. _sec-faq:


FAQ / Troubleshooting
******************************

**Which packages do I need to install to write and submit virtual prototypes?**

For writing scripts and submitting them to the SimBricks Cloud you need
``simbricks-orchestration``, ``simbricks-client`` and ``simbricks-cli``, plus the Python packages
of the components your script imports (e.g. ``simbricks-qemu-sim-py``, ``simbricks-i40e-sys-py``).
All of these are pure Python and installable via pip or conda. The simulator *binaries* are only
needed where the simulation actually executes — on the Runners, or on your machine for local
execution (see :ref:`sec-conda-packages`).

**My script fails with** ``AttributeError: module 'simbricks.orchestration.simulation' has no attribute 'QemuSim'`` **(or similar).**

Concrete simulator and device classes no longer live in ``simbricks-orchestration``. They come
from the component packages under ``simbricks.components.*``, e.g.
``from simbricks.components.qemu import simulation as qemu_sim`` for ``QemuSim``. Install the
respective ``simbricks-<x>-...-py`` package and update your imports (see
:ref:`sec-orchestration-framework-components`).

**Local execution fails because a simulator executable (e.g.** ``simb_net_switch`` **) is not found.**

The orchestration framework resolves simulator executables through ``$PATH``. Install the
component's binary conda package (e.g. ``simbricks-net-base-sim-bin``) from the SimBricks conda
channel into the active environment, or run inside the ``simbricks/simbricks-executor`` container
(see :ref:`sec-setup-compile`).

**Local execution fails with** ``RuntimeError: Global input directory is not set`` **or cannot find a disk image.**

``DistroDiskImage`` resolves images inside the global input directory. Pass
``--global-input-dir <dir>`` to ``simbricks-run``, where ``<dir>`` contains
``images/<name>/<name>`` as produced by the :image-builder:`\ ` tool (see
:ref:`sec-disk-images`).

**QEMU is very slow / warns that KVM is not available.**

Fast functional simulation with QEMU uses KVM. Make sure ``/dev/kvm`` exists and is accessible
(when using Docker, pass ``--device /dev/kvm``). Inside VMs, nested virtualization must be
enabled. Without KVM, QEMU falls back to slower binary translation (TCG) — simulations still work,
just slower.

**gem5 complains about the disk image or kernel.**

gem5 only supports **raw** disk images (build them with ``CONVERT_RAW=true`` in image-builder) and
boots the ELF ``vmlinux`` from ``images/<name>/boot/vmlinux``. Also note that gem5 needs to run
with ``kernel.perf_event_paranoid`` set to 1 or lower on the host (``sudo sysctl -w
kernel.perf_event_paranoid=1``); in Docker this typically requires ``--privileged``.

**My performance measurements are not reproducible / look wrong.**

By default SimBricks executes virtual prototypes *unsynchronized*, which is only meant for
functional testing. Enable synchronization in your Simulation Configuration for meaningful
end-to-end measurements (see :ref:`sec-orchestration-framework-sim-conf`).

**Where do I find the outputs of a run?**

For cloud execution, outputs are stored by the Backend and retrievable via CLI, client library, or
the web UI. For local execution, everything is collected under the working directory (default
``./out/``), with the aggregated simulation output in ``output/out.json`` (see
:ref:`sec-disk-images`).

**Something else is broken — where do I get help?**

Ask on :slack:`Slack` or open an issue/discussion on GitHub
(:simbricks-repo-plain:`simbricks/simbricks <>`). Bug reports with the full simulation output and
your virtual prototype script are the easiest to help with.

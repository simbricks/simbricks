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

.. _sec-orchestration-framework:

Orchestration Framework for Virtual Prototypes
**********************************************

SimBricks provides users with a powerful orchestration framework to programmatically define and configure virtual prototypes through Python scripts.
To do this, users leverage the ``simbricks-orchestration`` Python package that offers an intuitive and flexible API, allowing for seamless virtual prototype configuration.

The orchestration framework package is divided into three modules that reflect SimBricks configuration abstractions, namely the :ref:`System Configuration <sec-orchestration-framework-sys-conf>`,
:ref:`Simulation Configuration <sec-orchestration-framework-sim-conf>`, and :ref:`Instantiation Configuration <sec-orchestration-framework-inst-conf>`:

- ``simbricks.orchestration.system``: For defining the system's structure through components, interfaces, and channels.
- ``simbricks.orchestration.simulation``: For assigning simulators to components and defining simulation behavior.
- ``simbricks.orchestration.instantiation``: For configuring how and where the virtual prototype is executed.

Consequently, scripts written by users typically adopt a three-part structure corresponding to these abstractions.

Importantly, the ``simbricks-orchestration`` package itself only contains the *generic* building
blocks: base classes and simulator-independent components such as ``LinuxHost``, ``EthSwitch``,
``SimplePCIeNIC``, disk images, and applications. The *concrete* device models and simulator
classes live in separate per-simulator component packages that plug into the shared
``simbricks.components.*`` namespace (see :ref:`sec-orchestration-framework-components` below).

We will now take a closer look at how the SimBricks orchestration framework works and examine some of its most important aspects in detail.

.. _sec-orchestration-framework-sys-conf:

System Configuration
==============================

The System Configuration defines the structure of the virtual prototype.
This structure typically reflects the structure of real physical systems and is organized similarly.

The System Configuration does not specify how the system will be simulated (that means the System Configuration does not make any simulator choices).
Instead it only **defines the blueprint of the virtual prototype and thus what the simulated system should look like**.

The System Configuration makes use of three key concepts:

- **Components:** Represent components of the virtual prototype, such as a Corundum NIC, a Linux-Host, or a Switch.
- **Interfaces:** Define interfaces between components through which they will communicate. An Interface could e.g. be a PCIe interface or an Ethernet interface.
- **Channels:** Channels connect interfaces and act as communication paths. These Channels are later upon execution transformed into shared memory queues that link simulator instances.

Channels are also where communication latencies are configured: each channel has a configurable
link latency (e.g. ``channel.set_latency(500, utils_base.Time.Nanoseconds)``), which applies to the
message flow between the two connected components. Some components have interfaces of different
link types — for example, a NIC has a PCIe interface to connect to a host and an Ethernet interface
to connect to the network — and the latencies can be configured individually per channel.

Hosts additionally reference :ref:`disk images <sec-disk-images>` that define the software they
boot and run, and applications (subclasses of ``Application``) that define the workload commands.

.. _sec-orchestration-framework-sim-conf:

Simulation Configuration
==============================

The Simulation Configuration determines how the Components from the System Configuration are simulated.
Therefore, the System Configuration must be defined beforehand.
Once that is done, each Component is assigned to a specific simulator. For example:

- A Corundum NIC could be simulated by a behavioral C++ simulator or an RTL simulator such as `Verilator <https://www.veripool.org/verilator/>`_.
- A host could be simulated using `QEMU <https://www.qemu.org/>`_ or other full-system simulators like `gem5 <https://www.gem5.org/>`_.

The ``simbricks.orchestration.simulation`` module provides the generic base classes for this
(``Simulation``, ``Simulator``, and the per-role bases ``HostSim``, ``NICSim``, ``PCIDevSim``,
``NetSim``), while the concrete simulator classes (e.g. ``QemuSim``, ``Gem5Sim``, ``I40eNicSim``,
``SwitchNet``, ``NS3Net``, ``CorundumVerilatorNICSim``) come from the component packages.

**Synchronization.** SimBricks' default behavior is to execute virtual prototypes unsynchronized,
which is sufficient for functional testing and fastest. For meaningful end-to-end performance
measurements, synchronization must be enabled, e.g. through
``sim.enable_synchronization(amount=500, ratio=utils_base.Time.Nanoseconds)`` on the ``Simulation``
object, which synchronizes all channels with the given synchronization period. Generally, for
accurate simulations, you want to configure the synchronization period to the same value as the
link latency: with a lower value you do not gain accuracy but send more synchronization messages
than necessary, while a higher value trades off accuracy for simulation performance. For more
information, refer to the section on synchronization in
:ref:`sec-simulator-integration-background`.

.. _sec-orchestration-framework-inst-conf:

Instantiation Configuration
==============================

The Instantiation Configuration specifies how the virtual prototype is executed, including execution details such as:

- Specification of simulation Fragments, i.e. groups of simulators that are executed together, which can be distributed across multiple Runners.
- Choice of the Runners responsible for the execution, by attaching ``runner_tags`` to a Fragment (the Backend then schedules the Fragment on a Runner carrying all those labels) or by selecting a specific fragment executor via ``fragment_executor_tag``.
- Proxies (TCP or RDMA) that connect Fragments running on different machines.
- Checkpointing behavior (``create_checkpoint`` / ``restore_checkpoint``) for simulators that support it, to skip e.g. the Linux boot in detailed host simulators.

.. _sec-orchestration-framework-components:

Component Packages: ``simbricks.components.*``
==============================================

Every integrated simulator ships as its own set of Python packages that extend the shared,
implicit ``simbricks.components`` namespace. The convention is:

- ``simbricks.components.<x>.system`` — *system side*: concrete component classes for the System
  Configuration, e.g. ``simbricks.components.i40e.system`` provides ``IntelI40eNIC`` and
  ``I40ELinuxHost``. These packages depend only on ``simbricks-orchestration``, so a system
  description can be written (and shared) without installing any simulator.
- ``simbricks.components.<x>.simulation`` — *simulation side*: the simulator classes for the
  Simulation Configuration, e.g. ``simbricks.components.qemu.simulation`` provides ``QemuSim``.
  Where a component has multiple simulators, they are separated in submodules, e.g.
  ``simbricks.components.i40e.simulation.behavioral`` for the behavioral model.

The distribution packages follow a matching naming scheme (see :ref:`sec-conda-packages`):
``simbricks-<x>-sys-py`` (system components), ``simbricks-<x>-sim[-<flavor>]-py`` (simulator
classes, with flavors like ``bm`` for behavioral model or ``rtl`` for RTL simulation), and
``simbricks-<x>-sim[-<flavor>]-bin`` (the actual simulator executable, needed only where the
simulation runs).

There is no plugin registry or discovery mechanism: you simply import the classes you need and use
them in your script. The executable of a simulator is found through the environment where the
simulation executes — installing the ``*-bin`` conda package places it in ``$PATH`` under exactly
the name the simulator class expects.

For a code example of how these pieces play together see the
:ref:`Quickstart <chap-quickstart-sec-create-vp>` and the :ref:`sec-abstractions` chapter.

..
  Copyright 2022 Max Planck Institute for Software Systems, and
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

###################################
gem5
###################################

`gem5 <https://www.gem5.org/>`_ is a modular computer architecture simulator
that can be configured to simulate a very broad range of different systems. For
now, we maintain our :gem5-fork:`own fork of gem5 <>` on GitHub, which contains
our SimBricks adapters, a Python configuration script for full system x86
simulations with SimBricks adapters, and a few other extensions, such as MSI-X
support. In the long term, we hope to upstream these changes.

SimBricks Adapters
==================
We have added SimBricks adapters for PCI and Ethernet. The source for these
adapters and additional helper code are in
:gem5-fork:`src/simbricks </tree/main/src/simbricks>` in the gem5 repo.

Common Functionality
--------------------
Much of the functionality for initialization and synchronization is agnostic to
the specific SimBricks protocol used. We have factored out this code into a
base class ``simbricks::base::Adapter`` that just implements the SimBricks base
protocol layer. The ``simbricks::base::GenericBaseAdapter`` class is a generic
helper class that casts incoming and outgoing messages to the appropriate type
specified in the template. Both adapters use this. Note that the adapters do not
extend this class, but instead inherit and implement the ``Interface`` member
class. The adapters then create an instance of the ``GenericBaseAdapter`` and
pass in a reference to themselves through the interface parameter in the
constructor.

The base adapter code also takes care of properly instantiating and connecting
multiple adapters. The ``simbricks::base::InitManager`` singleton object,
collects references to all adapters and exposes functions to wait until a
specific adapter is ready and connected. The ``InitManager`` does this
asynchronously to avoid deadlocks due to mismatched initialization order in
different simulators.

Ethernet
--------
The Ethernet adapter implements a gem5 ``EtherInt`` port, through which it can
be connected to gem5-internal NICs. We have tested this with gem5's e1000 NIC.
The adapter is implemented in ``simbricks::ethernet::Adapter``. This adapter is
also a good starting point for future adapters, as it is simple but demonstrates
how to use the base adapter functionality, and both receives and sends messages.

PCI
----
The PCI adapter ``simbricks::pci::adapter`` is more complicated as it handles
many more message types and interacts with the re st of gem5 in multiple ways
(MMIO, DMA, Interrupts).

To make matters worse, it also does some gymnastics to implement a PCI device in
gem5 that uses the asynchronous timing memory protocol in gem5, instead of the
default atomic protocol semantics for PCI devices in gem5. For this we override
the MMIO port created by the PCI device super class, and implement our own
timing port. Hopefully, in the future, gem5 will offer a less backward way of
doing this but for now it works without drastically changing gem5's abstractions
and all the other devices using them.

Configuration
=============
gem5 is configured through Python scripts. These scripts can be parametrized
through the command line. Part of the configuration can be specified and adapted
by varying the command line parameters, while many will require you to directly
change the Python configurations. We include our reference configuration for x86
full system simulation capable of running Linux and with various SimBricks
adapter configurations in ``configs/simbricks/simbricks.py``. This script
heavily includes parts of the common gem5 configuration.


.. _sec-checkpointing:

Checkpointing
=============

gem5 supports checkpoint and restore. The most common use-case for this is
accelerating repeated simulations by checkpointing system state after boot and
running future simulations from there. Note that SimBricks does not currently
support distributed checkpoints. To leverage this feature for accelerating boot,
we carefully configure our simulations to checkpoint before executing anything
that affects state in other simulators, in particular before loading device
drivers. On resume, each gem5 instance will restore from its own checkpoint
while the rest of the simulators will just start again from their respective
initial state. As this state never changed in the checkpointed system either for
these components, this is still a consistent system state.

Usage Notes
===========
  * gem5 only supports raw hard disk images. The SimBricks Makefile contains
    commands to build the raw images from the qcow2 images. (see section 
    :ref:`sec-convert-qcow-images-to-raw`)

  * gem5-kvm simulations require ``kvm`` support on the host and appropriate
    permissions for the user to access ``/dev/kvm``. Note that unlike QEMU, gem5
    will fail with an error and not silently fall back to something slower.

  * gem5-kvm configurations require ``/proc/sys/kernel/perf_event_paranoid`` to
    be set to ``1`` or lower on the host system. :ref:`sec-gem5-perf` describes
    how to do so.

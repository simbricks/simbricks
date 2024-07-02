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

.. _sec-orchestration:

###################################
SimBricks Orchestration
###################################

Our orchestration framework replaces hand-crafted scripts for setting up and
running experiments. Instead, experiments are described in a declarative
fashion. The orchestration framework then takes care of the details, manages
launching the respective component simulators, sets up the SimBricks
communication channels between them, and monitors their execution. All output is
collected in a JSON file, which allows easy post-processing afterwards. 

******************************
Concepts
******************************

To declare experiments, we use multiple important concepts and terminology,
which we now introduce.

Experiments
===========

An *experiment* defines which component simulators to run and how they are
connected. To define one, instantiate the class
:class:`~simbricks.orchestration.experiments.Experiment` in your own Python
module, which has member functions to further define the component simulators to
run. SimBricks comes with many pre-defined experiments, which can serve as
starting guides and are located in the repository under
:simbricks-repo:`experiments/pyexps </blob/main/experiments/pyexps>`.

.. autoclass:: simbricks.orchestration.experiments.Experiment
  :members: add_host, add_pcidev, add_nic, add_network, checkpoint

Runs
====

Experiments can be executed multiple times, for example, to gain statistical
insights when including a random or non-deterministic component. We call each
execution a *run* of the experiment. Each run produces its own output JSON file.
The file name includes the number of the run.

The number of runs can be specified when invoking
:simbricks-repo:`experiments/run.py </blob/main/experiments/run.py>`. When using
simulator checkpointing, we use one run to boot the simulator and take the
checkpoint, and a second one to carry out the actual experiment. This is the
reason for two output JSON files being produced in this case. For more
information, see :ref:`sec-checkpointing`.

Component Simulators
====================

SimBricks defines multiple, ready-to-use component simulators in the module
:mod-orchestration:`simulators.py`. These include host, NIC, network, and PCIe
device simulators. Each simulator is defined by a class deriving from
:class:`~simbricks.orchestration.simulators.Simulator`, which provides the
necessary commands for their execution. We also offer more specialized base
classes for the different component types, which implement common member
functions, for example, to connect NICs or network component simulators to a
host simulator.

.. autoclass:: simbricks.orchestration.simulators.Simulator
  :members: prep_cmds, run_cmd, resreq_cores, resreq_mem

.. autoclass:: simbricks.orchestration.simulators.HostSim
  :members: sync_mode, sync_period, pci_latency, add_pcidev, add_nic, add_netdirect
  :show-inheritance:

.. autoclass:: simbricks.orchestration.simulators.NetSim
  :members: sync_mode, sync_period, eth_latency, connect_network
  :show-inheritance:

.. autoclass:: simbricks.orchestration.simulators.PCIDevSim
  :members: sync_mode, sync_period, pci_latency
  :show-inheritance:

.. autoclass:: simbricks.orchestration.simulators.NICSim
  :members: eth_latency, set_network
  :show-inheritance:

.. _sec-node_app_config:

*******************
Node and App Config
*******************

To configure the workload and the software environment of nodes, use the classes
:class:`~simbricks.orchestration.nodeconfig.NodeConfig` and
:class:`~simbricks.orchestration.nodeconfig.AppConfig`. The former is passed to
every host simulator and defines, for example, the networking configuration like
IP address and subnet mask, how much system memory the node has, but also which
disk image to run. You can read more about the latter under :ref:`sec-images`.

The :class:`~simbricks.orchestration.nodeconfig.NodeConfig` contains an
attribute for an instance of
:class:`~simbricks.orchestration.nodeconfig.AppConfig`, which defines the
workload or the concrete commands that are executed on the node. You can also
override :meth:`~simbricks.orchestration.nodeconfig.AppConfig.config_files` to
specify additional files to be copied into the host. These are specified as key
value pairs, where the key represents the path/filename inside the simulated
guest system and the value is an IO handle of the file to be copied over.

.. autoclass:: simbricks.orchestration.nodeconfig.NodeConfig
  :members: ip, prefix, mtu, cores, memory, disk_image, app, run_cmds,
    cleanup_cmds, config_files 

.. autoclass:: simbricks.orchestration.nodeconfig.AppConfig
  :members: run_cmds, config_files

*******************************
Unsynchronized vs. Synchronized
*******************************

SimBricks offers two modes of operation, unsynchronized and synchronized, which
are defined on a per component basis. The default is the unsynchronized mode
that is meant purely for functional testing. Unsynchronized components advance
virtual time as quickly as they possibly can, which means that measurements
taken on them are meaningless and cross-component measurements inaccurate.

The synchronized mode, in contrast, is meant for accurate measurements and has
to be enabled per component, for example, by setting
:attr:`simbricks.orchestration.simulators.PCIDevSim.sync_mode` or
:attr:`simbricks.orchestration.simulators.HostSim.sync_mode`. Running
synchronized means that a simulator waits to process incoming messages from
connected simulators at the correct timestamps. For technical details, see
:ref:`sec-synchronization`.

***************************************
Link Latency and Synchronization Period
***************************************

Most of the pre-defined simulators in :mod-orchestration:`simulators.py` provide
an attribute for tuning link latencies and the synchronization period. Both are
configured in nanoseconds and apply to the message flow from the configured
simulator to connected ones.

Some simulators have interfaces for different link types, for example, NIC
simulators based on :class:`~simbricks.orchestration.simulators.NICSim` have a
PCIe interface to connect to a host and an Ethernet link to connect to the
network. The link latencies can then be configured individually per interface
type.

The synchronization period defines the simulator's time between sending
synchronization messages to connected simulators. Generally, for accurate
simulations, you want to configure this to the same value as the link latency.
This ensures an accurate simulation. With a lower value we don't lose accuracy,
but we send more synchronization messages than necessary. The other direction is
also possible to increase simulation performance by trading-off accuracy using a
higher setting. For more information, refer to the section on
:ref:`sec-synchronization` in the :ref:`page-architectural-overview`.

.. _sec-images:

******************************
Images
******************************

All our host simulators boot up a proper Operating System and therefore require
a disk image. We already provide a minimal base image using Ubuntu and some
experiment-specific derivatives with additional packages installed. If you just
want to copy in additional files for your experiment, such as drivers and
executables, you don't need to build your own image. You can just override the
method :meth:`~simbricks.orchestration.nodeconfig.NodeConfig.config_files` of
:class:`~simbricks.orchestration.nodeconfig.AppConfig` or
:class:`~simbricks.orchestration.nodeconfig.NodeConfig` to mount additional
files under ``/tmp/guest`` inside the simulated OS.

For anything more than that, for example to install additional packages, you
need to build your own image. You can find information on how to do so under
:ref:`sec-howto-custom_image`. The specific image that you want to use for a
host in your experiment is specified in the
:class:`~simbricks.orchestration.nodeconfig.NodeConfig` class via the attribute
:attr:`~simbricks.orchestration.nodeconfig.NodeConfig.disk_image`.

*************************************
Checkpoints
*************************************

Some of our host simulators support taking checkpoints. Using these can
dramatically speed up the boot process by executing two runs for an experiment.
In the first, the simulator is booted in unsynchronized mode using an inaccurate
CPU model. When the boot process is completed meaning the workload defined via
the class :class:`~simbricks.orchestration.nodeconfig.AppConfig` can be
executed, a checkpoint is taken. In the second run, the simulator is switched
into synchronized mode, the CPU model replaced with the accurate one, and the
workload executed. Checkpointing can be enabled by setting the attribute
:attr:`~simbricks.orchestration.experiments.Experiment.checkpoint` on the
:class:`~simbricks.orchestration.experiments.Experiment` class.

When running an experiment multiple times, e.g. because you are tweaking the
workload, the checkpoint doesn't have to be recreated all the time. When
invoking the
:simbricks-repo:`orchestration framework </blob/main/experiments/run.py>`
without the ``--force`` flag, it won't re-execute experiments and runs for which
an output JSON file already exists. So if you delete only the output file of the
second run, you can save the time for creating the checkpoint.

******************************
Distributed Simulations
******************************

For the moment, refer to our
:simbricks-repo:`GitHub Q&A on this topic </discussions/73#discussioncomment-6682260>`.

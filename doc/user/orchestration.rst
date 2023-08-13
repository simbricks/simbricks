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
starting guides and are located in the repository under ``experiments/pyexps``.

.. autoclass:: simbricks.orchestration.experiments.Experiment
  :members: add_host, add_pcidev, add_nic, add_network

Runs
====

Experiments can be executed multiple times, for example, to gain statistical
insights when including a random or non-deterministic component. We call each
execution a *run* of the experiment. Each run produces its own output JSON file.
The file name includes the number of the run.

The number of runs can be specified when invoking the orchestration framework,
see :ref:`sec-command-line`. When using simulator checkpointing, we use one run
to boot the simulator and take the checkpoint, and a second one to carry out the
actual experiment. This is the reason for two output JSON files being produced
in this case. For more information, see :ref:`sec-checkpointing`.

Component Simulators
====================

SimBricks comes with multiple, ready-to-use component simulators for your
experiments in :mod:`simbricks.orchestration.simulators`. These include host,
NIC, network, and PCIe device simulators. On the orchestration side, each
simulator is implemented in a class deriving from
:class:`~simbricks.orchestration.simulators.Simulator`, which provides the
necessary commands for their execution. We also offer more specialized base
classes for the different component types, which implement common member
functions, for example, to connect NICs or network component simulators to a
host simulator.

.. automodule:: simbricks.orchestration.simulators
  
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
disk image to run. You can read more about the latter under
:ref:`sec-howto-custom_image`.

The :class:`~simbricks.orchestration.nodeconfig.NodeConfig` contains an
attribute for an instance of
:class:`~simbricks.orchestration.nodeconfig.AppConfig`, which defines the
workload or the concrete commands that are executed on the node. You can also
override :meth:`~simbricks.orchestration.nodeconfig.AppConfig.config_files` to
specify additional files to be copied into the host. These are specified as key
value pairs, where the key represents the path/filename inside the simulated
guest system and the value is an IO handle of the file to be copied over.

.. automodule:: simbricks.orchestration.nodeconfig

.. autoclass:: simbricks.orchestration.nodeconfig.NodeConfig
  :members: ip, prefix, mtu, cores, memory, disk_image, app, run_cmds,
    cleanup_cmds, config_files 

.. autoclass:: simbricks.orchestration.nodeconfig.AppConfig
  :members: run_cmds, config_files

*******************************
Synchronized vs. Unsynchronized
*******************************

For most component simulators in your experiment, you can decide whether to run
them synchronized or unsynchronized by setting
:attr:`~simbricks.orchestration.simulators.PCIDevSim.sync_mode` or
:attr:`~simbricks.orchestration.simulators.QemuHost.sync`. By default, all
simulators run unsynchronized to simulate as fast as possible. When you are
conducting measurements, however, you need to run synchronized, or you won't get
meaningful performance numbers.

Running synchronized means that a simulator waits to process incoming messages
from connected simulators at the correct timestamps. For technical details, see
:ref:`sec-synchronization`. In contrast, unsynchronized lets a simulator advance
its virtual time as fast as it can. It still handles and exchanges messages with
connected simulators, but it won't wait for incoming messages and instead
advances its virtual time when there's nothing available to process. 

***************************************
Link Latency and Synchronization Period
***************************************

Most of the pre-defined simulators in :mod:`simbricks.orchestration.simulators`
provide an attribute for tuning link latencies and the synchronization period.
Both are configured in nanoseconds and apply to the message flow from the
configured simulator to connected ones.

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


.. _sec-command-line:

******************************
Running Experiments
******************************

To run experiments using our orchestration framework, use the
``experiments/run.py`` script. For your convenience, you can also use
``simbricks-run`` in the Docker images from anywhere to run experiments. In
practice, running experiments will look similar to this:

.. code-block:: bash

  $ python run.py --verbose --force pyexps/simple_ping.py
  # only available inside docker images
  $ simbricks-run --verbose --force pyexps/simple_ping.py

Here are all the command line arguments for the ``experiments/run.py`` script:

.. code-block:: text

  usage: run.py [-h] [--list] [--filter PATTERN [PATTERN ...]] [--pickled] [--runs N]
                [--firstrun N] [--force] [--verbose] [--pcap] [--repo DIR] [--workdir DIR]
                [--outdir DIR] [--cpdir DIR] [--hosts JSON_FILE] [--shmdir DIR]
                [--parallel] [--cores N] [--mem N] [--slurm] [--slurmdir DIR] [--dist]
                [--auto-dist] [--proxy-type TYPE]
                EXP [EXP ...]

  positional arguments:
    EXP                   Python modules to load the experiments from

  options:
    -h, --help            show this help message and exit
    --list                List available experiment names
    --filter PATTERN [PATTERN ...]
                          Only run experiments matching the given Unix shell style patterns
    --pickled             Interpret experiment modules as pickled runs instead of .py files
    --runs N              Number of repetition of each experiment
    --firstrun N          ID for first run
    --force               Run experiments even if output already exists (overwrites output)
    --verbose             Verbose output, for example, print component simulators\' output
    --pcap                Dump pcap file (if supported by component simulator)

  Environment:
    --repo DIR            SimBricks repository directory
    --workdir DIR         Work directory base
    --outdir DIR          Output directory base
    --cpdir DIR           Checkpoint directory base
    --hosts JSON_FILE     List of hosts to use (json)
    --shmdir DIR          Shared memory directory base (workdir if not set)

  Parallel Runtime:
    --parallel            Use parallel instead of sequential runtime
    --cores N             Number of cores to use for parallel runs
    --mem N               Memory limit for parallel runs (in MB)

  Slurm Runtime:
    --slurm               Use slurm instead of sequential runtime
    --slurmdir DIR        Slurm communication directory

  Distributed Runtime:
    --dist                Use sequential distributed runtime instead of local
    --auto-dist           Automatically distribute non-distributed experiments
    --proxy-type TYPE     Proxy type to use (sockets,rdma) for auto distribution

******************************
Images
******************************


******************************
Distributed Simulations
******************************


******************************
Slurm
******************************

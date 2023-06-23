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
running experiments. Instead, they are described in a declarative fashion. The
orchestration framework then takes care of the details managing launching the
respective component simulators, setting up the SimBricks communication channels
between them, and monitoring their execution. All output is collected in a JSON
file, which allows post-processing afterwards. 

******************************
Concepts
******************************

To declare experiments, we use multiple important concepts and terminology,
which we now introduce.

Experiments
===========

An *experiment* defines which component simulators to run, how they are
connected, and which workload is executed. To define an experiment, instantiate
the class :class:`~simbricks.orchestration.experiments.Experiment` in your own
Python module, which has member functions to further define the component
simulators to run. SimBricks comes with many pre-defined experiments, which can serve as starting guides and are located in the repository under ``experiments/pyexps``.

.. autoclass:: simbricks.orchestration.experiments.Experiment
  :members: add_host, add_pcidev, add_nic, add_network

Runs
====

Experiments can be executed multiple times, for example, to gain statistical
insights when including a random or non-deterministic component. We call each
execution one *run* of the experiment. Each run produces its own output JSON
file. The file name includes the number of the run.

The number of runs can be specified when invoking the orchestration framework,
see :ref:`sec-command-line`. When using simulator checkpointing, we use one run
to boot the simulator and take the checkpoint, and a second one to execute the
actual experiment. This is the reason for two output JSON files being produced.
For more information, see :ref:`sec-checkpointing`.

Component Simulators
====================

SimBricks provides multiple already implemented component simulators, which
can be used in experiments. This selection includes host, NIC, network, and PCI
device simulators. Each simulator is implemented in a class deriving from
:class:`~simbricks.orchestration.simulators.Simulator`, which provides the
necessary commands and arguments for its execution and for specifying the
SimBricks communication channel to connect to. We also offer more specialized
base classes for the different component types, which implement common member
functions, for example, add connected NICs or network component simulators to a
host component simulator. Every already implemented component simulator can be
found in the module. :mod:`simbricks.orchestration.simulators`.

.. automodule:: simbricks.orchestration.simulators

  .. autoclass:: simbricks.orchestration.simulators.Simulator
    :members: resreq_cores, resreq_mem, prep_cmds, run_cmd, dependencies

  .. autoclass:: simbricks.orchestration.simulators.HostSim
    :members: add_pcidev, add_nic, add_netdirect

  .. autoclass:: simbricks.orchestration.simulators.NICSim
    :members: set_network

  .. autoclass:: simbricks.orchestration.simulators.NetSim
    :members: connect_network

  .. autoclass:: simbricks.orchestration.simulators.PCIDevSim


.. _sec-node_configuration:

Node Configuration
==================

The configuration and workload to run on individual host simulators or, more
generally, nodes that should run in the experiment, are defined using the
classes :class:`~simbricks.orchestration.nodeconfig.NodeConfig` and
:class:`~simbricks.orchestration.nodeconfig.AppConfig`, respectively.

:class:`~simbricks.orchestration.nodeconfig.NodeConfig` defines, for example,
the networking configuration like IP address and subnet mask, how much system
memory the node has, and which disk image to run. The latter can be used, for
example, to run a specific version of the Linux kernel on a node. You can find
more information on this in the :ref:`next section <sec-howto-custom_image>`.
:class:`~simbricks.orchestration.nodeconfig.NodeConfig` contains an attribute
for a :class:`~simbricks.orchestration.nodeconfig.AppConfig`.

.. automodule:: simbricks.orchestration.nodeconfig

  .. autoclass:: simbricks.orchestration.nodeconfig.NodeConfig
    :members: ip, prefix, mtu, cores, memory, disk_image, app, run_cmds, cleanup_cmds, config_files 


.. _sec-app_configuration:

Application Configuration
-------------------------

The class :class:`~simbricks.orchestration.nodeconfig.AppConfig` offers member
functions to define the concrete commands to run on the node. It also provides a
member function
:meth:`~simbricks.orchestration.nodeconfig.AppConfig.config_files` to specify
additional files to be made available on the host, which are specified as key
value pairs, where the key represents the filename inside the simulated guest
system and the value is an IO handle to the file on the host running the
simulators.

  .. autoclass:: simbricks.orchestration.nodeconfig.AppConfig
    :members: run_cmds, config_files


******************************
Running Experiments
******************************


.. _sec-command-line:

Command Line
====================

To run experiments using our orchestration framework, use the
``experiments/run.py`` script. For your convenience, you can also use
``simbricks-run`` in the Docker images from anywhere to run experiments. In
practice, running experiments will look similar to this:

.. code-block:: bash

  $ python3.10 run.py --verbose --force pyexps/qemu_i40e_pair.py
  # only available inside docker images
  $ simbricks-run --verbose --force qemu_i40e_pair.py

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

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

.. _sec-howto:

###################################
How To
###################################


.. _sec-howto-createrun:

******************************
Create and Run an Experiment
******************************

Experiments are defined in a declarative fashion inside Python modules using
classes. Basically, create a `.py` file and add a global variable
``experiments``, a list which contains multiple instances of the class
:class:`~simbricks.orchestration.experiments.Experiment`, each one describing a
standalone experiment. This is very helpful if you wish to evaluate your work in
different environments, for example, you may want to swap out some simulator or
investigate multiple topologies with different scale. 

The class :class:`~simbricks.orchestration.experiments.Experiment` provides
methods to add the simulators you wish to run. All available simulators can be
found in the module :mod-orchestration:`simulators.py`. Instantiating
:class:`~simbricks.orchestration.simulators.HostSim` requires you to specify a
:class:`~simbricks.orchestration.nodeconfig.NodeConfig`, which contains the
configuration for your host, for example, its networking settings, how much
system memory it should have, and most importantly, which applications to run by
assigning an :class:`~simbricks.orchestration.nodeconfig.AppConfig`. You can
find predefined classes for node and app configs in the module
:mod-orchestration:`nodeconfig.py`. Feel free to add new ones or just create a
new class locally in your experiment's module. For more details, see
:ref:`sec-orchestration`.

The last step to complete your virtual testbed is to specify which virtual
components connect to each other. You do this by invoking the respective methods
on the simulators you have instantiated. See the different simulator types' base
classes in the module :mod-orchestration:`simulators.py` for more information. A
simple and complete experiment module in which a client host pings a server can
be found :ref:`below <simple_ping_experiment>`.

If you plan to simulate a topology with multiple hosts, it may be helpful to
take a look at the module :mod-orchestration:`simulator_utils.py` in which we
provide some helper functions to reduce the amount of code you have to write.

Finally, to run your experiment, invoke
:simbricks-repo:`experiments/run.py </blob/main/experiments/run.py>`
and provide the path to your experiment module. In our docker containers, you
can also just use the following command from anywhere:

.. code-block:: bash

  $ simbricks-run --verbose --force <path_to_your_module.py>

``--verbose`` prints all simulators' output to the terminal and ``--force``
forces execution even if there already exist result files for the experiment. If
``simbricks-run`` is not available, you can always do 

.. code-block:: bash
  
  $ cd experiments
  $ python run.py --verbose --force <path_to_your_module.py>

While running, you can interrupt the experiment using Ctrl+C in your terminal.
This will cleanly stop all simulators and collect their output in a JSON file in
the directory ``experiments/out/<experiment_name>``. These are the necessary
basics to create and run your first experiment. Have fun.

.. literalinclude:: /../experiments/pyexps/simple_ping.py
  :linenos:
  :lines: 29-
  :language: python
  :name: simple_ping_experiment
  :caption: A simple experiment with a client host pinging a server, both are
    connected through a network switch. The setup of the two hosts could be
    simplified by using
    :func:`simbricks.orchestration.simulator_utils.create_basic_hosts`.

.. _sec-howto-nodeconfig:

********************************
Add a Node or Application Config
********************************

A host's configuration and the workload to run are defined via
:ref:`sec-node_app_config`. SimBricks already comes with a few examples in the
module :mod-orchestration:`nodeconfig.py`. If they don't fit your use-case, you
need to add your own by overriding the pre-defined member functions of
:class:`~simbricks.orchestration.nodeconfig.NodeConfig` and
:class:`~simbricks.orchestration.nodeconfig.AppConfig`. The most important one
is :meth:`~simbricks.orchestration.nodeconfig.AppConfig.run_cmds`, which defines
the commands to execute for your workload/application. Further information can
be found in the module :mod-orchestration:`nodeconfig.py` directly.

.. _sec-howto-custom_image:

******************************
Add a Custom Image
******************************

******************************
Integrate a New Simulator
******************************

The first step is to implement a SimBricks adapter in the simulator you want to
integrate. This adapter on one side uses the simulator's extension API to act as
a native device and on the other side sends and receives SimBricks messages. You
can find more information on adapters in our :ref:`page-architectural-overview`.

To make running experiments and setting up the SimBricks communication channels
to other simulators convenient, add a class for the simulator in
:mod-orchestration:`simulators.py`` that inherits either from
:class:`~simbricks.orchestration.simulators.Simulator` or one of the more
specialized base classes in. In this class, you define the command(s) to execute
the simulator together with further parameters, for example, to connect to the
communication channels with other simulators. Below is an example of what this
looks like.

.. code-block:: python
  :linenos:
  :caption: Orchestration framework class for WireNet, a simple Ethernet wire
    that attaches to the SimBricks Ethernet adapters of two simulators.

  class WireNet(NetSim):

    def run_cmd(self, env):
        connects = self.connect_sockets(env)
        assert len(connects) == 2
        cmd = (
            f'{env.repodir}/sims/net/wire/net_wire {connects[0][1]}'
            f' {connects[1][1]} {self.sync_mode} {self.sync_period}'
            f' {self.eth_latency}'
        )
        if env.pcap_file:
            cmd += ' ' + env.pcap_file
        
        return cmd


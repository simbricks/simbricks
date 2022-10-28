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
:class:`simbricks.orchestration.experiments.Experiment`, each one describing a
standalone experiment. This is very helpful if you wish to evaluate your work in
different environments, for example, you may want to swap out some simulator or
investigate multiple topologies with different scale.

The class :class:`~simbricks.orchestration.experiments.Experiment` provides
methods to add the simulators you wish to run. All available simulators can be
found in the module :mod:`simbricks.orchestration.simulators`. Instantiating
:class:`~simbricks.orchestration.simulators.HostSim` requires you to specify a
:class:`~simbricks.orchestration.nodeconfig.NodeConfig`, which contains the
configuration for your host, for example its networking settings, how much
system memory it should have, and most importantly, which application to run by
assigning an :class:`~simbricks.orchestration.nodeconfig.AppConfig`. You can
find predefined classes for node and app configs in the module
:mod:`simbricks.orchestration.nodeconfig`, feel free to add new ones or just
create a new class locally in your experiment's module.

The last step to complete your virtual testbed is to specify which virtual
components connect to each other. You do this by invoking the respective methods
on the simulators you have instantiated. See the different simulator types' base
classes in the module :mod:`~simbricks.orchestration.simulators` for more
information. A simple and complete experiment module in which a client host
pings a server can be found :ref:`below <simple_ping_experiment>`.

If you plan to simulate a topology with multiple hosts, it may be helpful to
take a look at the module :mod:`simbricks.orchestration.simulator_utils` in
which we provide some helper functions to reduce the amount of code you have to
write.

Finally, to run your experiment invoke ``/experiments/run.py`` and provide the
path to your experiment module. In our docker containers, you can just use the
following command from anywhere:

.. code-block:: bash

  $ simbricks-run --verbose --force <path_to_your_module.py>

``--verbose`` prints all simulators' output to the terminal and ``--force``
forces execution even if there already exist result files for the same
experiment. If ``simbricks-run`` is not available, you can always do 

.. code-block:: bash
  
  # from the repository's root directory
  $ cd experiments
  $ python run.py --verbose --force <path_to_your_module.py>

While running, you can interrupt the experiment using CTRL+C in your terminal.
This will cleanly stop all simulators and collect their output in a JSON file in
the directory ``experiments/out/<experiment_name>``. These are the necessary
basics to create and run your first experiment. Have fun.

.. literalinclude:: /../experiments/pyexps/simple_ping.py
  :linenos:
  :lines: 25-
  :language: python
  :name: simple_ping_experiment
  :caption: A simple experiment with a client host pinging a server, both are
    connected through a network switch. The setup of the two hosts could be
    simplified by using
    :func:`~simbricks.orchestration.simulator_utils.create_basic_hosts`.

.. _sec-howto-nodeconfig:

********************************
Add a Node or Application Config
********************************

******************************
Add a Custom Image
******************************

******************************
Integrate a New Simulator
******************************

The first step when integrating a new simulator into SimBricks is to implement a
SimBricks adapter for it. You can find the necessary information in the
:ref:`Simulator Adapters <Simulator Adapters>` section. After that, we need to
add a class for the simulator in the SimBricks orchestration framework such that
it can be used when defining experiments. This class basically wraps a command
for launching the simulator and needs to inherit from
:class:`~simbricks.orchestration.simulators.Simulator` and implement relevant
methods. There are several more specialized child classes in the module
:mod:`simbricks.orchestration.simulators` for typical categories of simulators,
which already offer the interfaces to collect parameters like which other
simulators to connect to necessary for creating the launch command. Examples are
:class:`~simbricks.orchestration.simulators.PCIDevSim`,
:class:`~simbricks.orchestration.simulators.NICSim`,
:class:`~simbricks.orchestration.simulators.NetSim`, and
:class:`~simbricks.orchestration.simulators.HostSim`. You can find an example
below of adding a class for the ``NS3`` network simulator.

.. code-block:: python
  :linenos:
  :caption: Class implementing the ``NS3`` network simulator in the SimBricks
    orchestration framework.

  class NS3BridgeNet(NetSim):

    def run_cmd(self, env):
        ports = ''
        for (_, n) in self.connect_sockets(env):
            ports += '--CosimPort=' + n + ' '

        cmd = (
            f'{env.repodir}/sims/external/ns-3'
            f'/cosim-run.sh cosim cosim-bridge-example {ports} {self.opt}'
        )
        print(cmd)

        return cmd


******************************
Add a New Interface
******************************

.. autoclass:: simbricks.orchestration.experiments.Experiment
  :members: add_host, add_pcidev, add_nic, add_network

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


.. automodule:: simbricks.orchestration.nodeconfig

  .. autoclass:: simbricks.orchestration.nodeconfig.NodeConfig
    :members:
    
  .. autoclass:: simbricks.orchestration.nodeconfig.AppConfig
    :members:

.. automodule:: simbricks.orchestration.simulator_utils
  :members:

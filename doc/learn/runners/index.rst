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


.. _sec-runner:

Runners
=======================

Runners are the core execution engines within the SimBricks architecture. They 
are responsible for the actual execution of virtual prototypes (VPs). While
users interface with the SimBricks Cloud through our Python API, the heavy
lifting of running complex, heterogeneous simulations occurs on Runners.

Because we support both SimBricks-hosted and self-hosted execution environments,
the Runner logic is entirely open-source. It is implemented in Python and can be
found in the main repository under ``symphony/runner/simbricks/runner``.

Resource Management and Scheduling
----------------------------------------

Runners are designed to allow safe and efficient resource sharing across
multiple users on the same infrastructure. 

When a user submits a virtual prototyping configuration to the SimBricks Backend,
the backend evaluates the resource requirements of the run. It then schedules
the execution on an available Runner that has sufficient capacity. 

To ensure stability and prevent Runners from overwhelming the host machines they
operate on, they can be strictly constrained via the backend. Administrators can
configure exact limits on the computational resources and memory a specific
Runner is allowed to allocate, ensuring predictable performance even in shared
environments.

Runner Architecture: Main vs. Fragment Runner
----------------------------------------------------------------------------

.. figure:: SimBricks-Runner-Architecture.png
  :width: 600

  Architectural Overview over Main and Fragment Runners.

To support highly complex and distributed simulations, SimBricks execution is
decoupled into **Main Runners** and **Fragment Runners**. 

Users have the option to split the execution of a virtual prototype across
multiple "Fragments." When a run is scheduled, a Main Runner takes charge of the
orchestration. It evaluates the configuration and spawns Fragment Runners on
demand to execute specific portions of the virtual prototype.

Splitting execution into fragments provides two major advantages:

1. **Distributed Simulation:** Fragments can be distributed across multiple
   Runners, allowing massive virtual prototypes (e.g., hundreds of simulated
   hosts) to scale horizontally across a cluster.
2. **Heterogeneous Environments:** Multiple fragments can be executed on the
   *same* Runner using different environments. For example, one fragment
   containing a specific simulator can run bare-metal on the host, while another
   fragment runs simultaneously inside an isolated Docker container.

Main Runner Plugins
----------------------------------------

To facilitate these heterogeneous environments, the Main Runner utilizes a
plugin system to determine how a Fragment Runner should be spawned. Currently,
SimBricks supports two primary plugins:

The Local Plugin
*********************************
The Local plugin is used for bare-metal execution. When this plugin is invoked,
the Main Runner spawns a Fragment Runner directly on the host OS. This approach
assumes that all required simulators and dependencies for that specific fragment
are natively installed on the machine the Runner is operating on.

The Docker Plugin
*********************************
The Docker plugin allows for highly modular, containerized execution. Instead of
relying on local host dependencies, you can specify Docker images that the Main
Runner will pull on the fly. These images contain the required simulators and
act as self-contained Fragment Runners. 

.. note::
  **Use Case: Corundum Integration**
  
  We utilize the Docker plugin in our Corundum example (available in the SimBricks
  examples repository :simbricks-examples:`\ ` ). This setup is incredibly
  powerful for custom hardware development. It allows teams to maintain and
  build their custom simulator integration in a completely separate repository,
  package it as a Docker image, and dynamically provide it to a SimBricks Runner
  without ever needing to modify the Runner's host environment.

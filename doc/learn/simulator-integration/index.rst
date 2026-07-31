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

.. _sec-simulator-integration:


Simulator Integration
******************************

SimBricks enables the creation of virtual prototypes by orchestrating, connecting and synchronizing multiple instances of already existing (or newly created)
simulators. To use them as part of the SimBricks platform, a user must integrate a respective simulator.

Integrated simulators live in their own *component repositories* (e.g. :component-corundum:`\ `,
:component-qemu:`\ `, :component-ns3:`\ `) and are distributed as installable packages, so
integrating a new simulator does **not** require changing the SimBricks core. An integration
consists of three parts:

1. An **Adapter** inside the simulator that implements the SimBricks protocol for the interfaces
   the simulator exposes (e.g. PCIe, Ethernet, memory) — see
   :ref:`sec-simulator-integration-background` and
   :ref:`sec-simulator-integration-implementation`.
2. A small **Python integration** into the orchestration framework, so the simulator can be used
   in virtual prototype scripts — classes under the ``simbricks.components.*`` namespace.
3. **Packaging** as a component repository with conda recipes, so users (and Runners) can simply
   install the simulator — see :ref:`sec-simulator-integration-packaging`.

On this page, we provide an overview of how SimBricks connects existing simulators into an end-to-end virtual prototype.
In the end, you should have all the required knowledge to extend SimBricks by integrating a new Simulator.

.. tip::
    In case you want to jump straight into the **implementation** details, check out the :ref:`sec-simulator-integration-implementation` section.


.. toctree::
   :maxdepth: 2

   background/index
   implementation/index
   packaging/index

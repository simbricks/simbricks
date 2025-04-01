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

.. _sec-architecture:

Architectural Overview
==============================

In this chapter we will give an architectural overview over the different pieces of SimBricks.

Currently the SimBricks architecture comprises three main parts: Frontend, Backend and Runners as shown in the figure below. 
In the following we will have an overview over the purpose of these pieces.


.. figure:: architecture.svg
  :width: 600

  Architectural Overview over the SimBricks Architecture 


Frontend
-------------------------------------------

Users use the SimBricks Frontend to configure virtual prototypes i.e. to define experiments and to trigger the execution of them. 

The Fontend itself is again composed of multiple important pieces:

* Python Orchestration Framework: Users configure virtual prototypes through our python :ref:`sec-orchestration-framework`. This means users can write 
                                  simple python scripts using the orchestration framework to define the experiments they want to run including (but not 
                                  limited to) the simulation topology, simulators and whether the simulation should be executed on multiple machines or not.
* Command-Line Interface (CLI): Once the virtual prototype configurations are ready, users submit them to the backend for execution. This can be done using the SimBricks 
                                :ref:`sec-cli-ref` tool. Users can opt to asynchronously retrieve the output and results at a later time, or handle them
                                synchronously as the virtual prototype runs. Besides the execution in the cloud SimBricks also supports the local **limited**
                                execution of virtual prototypes locally through the command line.
* Python Client Library: Instead of sending virtual prototype configurations via the CLI to the backend, users can use our Client Library directly within the python
                         scripts that define their virtual prototypes in order to send it to the backend for execution. This does also offer the flexibility to process
                         the results conviniently through python scripts.
* Graphical User Interface (GUI): Looking ahead, we plan to extend SimBricks by introducing a graphical web-based frontend, that enables graphical configuration and 
                                  interaction with virtual prototypes.

.. 
  Virtual Prototyping Orchestration Framework
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  CLI
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  On-Premise
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Runner
-------------------------------------------

Backend
-------------------------------------------

Core Library
-------------------------------------------
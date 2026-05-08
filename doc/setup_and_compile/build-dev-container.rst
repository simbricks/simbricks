..
  Copyright 2021 Max Planck Institute for Software Systems, and
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


Building in a VS Code Dev Container
===================================

**We highly recommend this approach if you plan to develop custom adapters,
modify the framework, or build new disk images.**

The SimBricks repository is pre-configured with a :dev-container:`\ ` that
includes all required dependencies for compiling and working with SimBricks. 

If you have Docker set up and the :dev-container-ext:`\ ` you can open SimBricks
inside a devcontainer in two simple steps:

1. Clone the repository and open it in VS Code.
2. Press ``Ctrl+Shift+P`` and execute the ``Dev Containers: Reopen in Container``
   command to open the repository inside the container. 

After this, all VS Code terminals will now automatically run commands inside the
fully configured container.

Compiling Core Components
-------------------------
To compile the core SimBricks components, run ``make`` (we recommend using ``-jN``
to utilize multiple cores).

This step will also build simulators directly contained in the SimBricks
repository. You likely also want to build at least some of the external
simulators (e.g. QEMU, ns-3), for this refer to 
:ref:`Compiling external simulators <sec-setup-compile-ext-sims>`.

.. note:: 
   By default, we do not build the Verilator simulation (as it takes several
   minutes to compile) and also skip building the RDMA proxy (as it depends on
   specific RDMA NIC libraries). 
   
   To enable these builds for your artifacts, set ``ENABLE_VERILATOR=y`` and 
   ``ENABLE_RDMA=y`` on the command line, or create a ``mk/local.mk`` file and 
   insert those settings there.


.. _sec-setup-compile-ext-sims:

Compiling External Simulators
-----------------------------
To build external simulators such as **gem5**, **QEMU**, or **ns-3** for your
custom workflows, first ensure their corresponding submodules are initialized:

.. code-block:: bash

   git submodule update --init

Then you can either build all external simulators at once (this may take
multiple hours depending on your machine):

.. code-block:: bash

   make -jN external

or alternatively, build them individually as needed (replace ``qemu`` with 
``gem5``, ``ns-3``, or ``femu``):

.. code-block:: bash

   make -jN sims/external/qemu/ready

Building Disk Images
--------------------

To generate custom disk images, use the following commands. 

.. note::
   This step requires QEMU to be built first.

   Be aware that these steps can again take 10 to 45 minutes depending on your
   machine and whether KVM acceleration is available.

   Unless you want to modify the images, you will only need to exectue this once.

To build **all** disk images that we provide out-of-the-box, run the following
command:

.. code-block:: bash

   make -jN build-images

Alternatively you can only build the base disk images (excluding the NOPaxos or
Memcached images):

.. code-block:: bash

   make -jN build-images-min


Installing the Python Orchestration Framework
---------------------------------------------
To utilize or modify the SimBricks orchestration framework, you must install its
corresponding Python packages into your environment. 

We highly recommend doing this by running the following command:

.. code-block:: bash

   make symphony-dev

This command performs an "editable" install of the orchestration packages. By
using an editable install, any modifications you make to the local Python source
code will be immediately reflected in your runtime environment, completely
eliminating the need to rebuild or reinstall the packages after every change.

Once you performed all these steps you are ready to run your first SimBricks 
simulation.

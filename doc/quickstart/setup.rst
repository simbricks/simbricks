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

.. _chap-quickstart-sec-setup:

Setup
******************************

.. hint::
  If you already set up your SimBricks environment, you can immediately proceed by :ref:`configuring your first virtual prototype <chap-quickstart-sec-create-vp>`

The examples within the Examples repository utilize the :ref:`SimBricks Cloud version <sec-architecture>`.
To run them as-is, you will need access to the SimBricks Demo Backend (or your own if already present).

To get access to the SimBricks Demo Backend, start by `registering for the SimBricks Demo <https://www.simbricks.io/demo/>`_.
The registration ensures you have the proper credentials to interact with the Backend.
This is necessary to send your virtual prototypes to our Backend such that the virtual prototype's execution will be scheduled on one of our Runners.

Once you got access to our Backend, you can proceed by cloning our `Examples Repository <https://github.com/simbricks/simbricks-examples>`_:

.. code-block:: bash

  git clone git@github.com:simbricks/simbricks-examples.git
  cd simbricks-examples

Option 1: Dev Container / GitHub Codespaces (no further setup)
==============================================================

The examples repository ships a pre-configured :dev-container:`\ `.
If you open the repository in VS Code with the :dev-container-ext:`\ ` installed (or directly in
`GitHub Codespaces <https://github.com/features/codespaces>`_), all required SimBricks Python
packages are installed automatically and you can skip straight ahead to
:ref:`creating your first virtual prototype <chap-quickstart-sec-create-vp>`.

Option 2: Manual setup with a Python virtual environment
========================================================

Alternatively, set up a `Python Virtual Environment <https://docs.python.org/3/tutorial/venv.html>`_ (Python 3.10 or newer).
You can create and activate a virtual environment as follows:

.. code-block:: bash

  python3 -m venv venv
  source venv/bin/activate

Then install the required SimBricks Python packages.
To run the examples given in the repository (or your own virtual prototypes), the following SimBricks packages are required:

- ``simbricks-orchestration``: For creating virtual prototype configurations as shown in the following.
- ``simbricks-client``: For sending configurations to the SimBricks server via Python.
- ``simbricks-cli``: For managing configurations via the terminal CLI.
- The Python packages of the component simulators an example uses, e.g. ``simbricks-qemu-sim-py``,
  ``simbricks-i40e-sys-py``, ``simbricks-i40e-sim-bm-py``, or ``simbricks-net-base-sim-py``.
  Since simulators no longer live inside the core packages, every virtual prototype script installs
  exactly the component packages it imports (see :ref:`sec-conda-packages` for the full package
  list and naming scheme).

You can conveniently install all packages needed by the examples using pip and the *requirements.txt* file we provide with the examples repository:

.. code-block:: bash

  pip install -r requirements.txt

.. note::
  The Python packages installed here are all you need for *writing* virtual prototypes and
  *submitting* them to the SimBricks Cloud, where the actual simulators run on our Runners.
  If you instead want to execute virtual prototypes on your own machine, you additionally need the
  simulator binaries, which are distributed through the SimBricks conda channel — see
  :ref:`sec-setup-compile`.

Your namespace
==============

The :ref:`SimBricks CLI and Client <sec-execution>` submit your runs to a namespace on the
Backend. When you register for the demo, we automatically create the namespace
``demo/<your demo email address>`` for you and configure it as your default — so there is
nothing you need to set up here.

.. note::
  If you ever want to work with a different namespace than your default, you can override it
  through the ``NAMESPACE`` environment variable, e.g.
  ``export NAMESPACE=demo/<your demo email address>``.

Optionally, you can also enable tab completion for the SimBricks CLI:

.. code-block:: bash

  simbricks-cli --install-completion

With the above steps completed, you are ready to dive into using SimBricks.

If you encounter any issues, feel free to `reach out to us directly <https://www.simbricks.io/join-slack>`_.

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

.. _chap-quickstart-sec-setup:

Setup
******************************

.. hint::
  If you already setup your SimBricks environment, you can immediately proceed by :ref:`configuring your first virtual prototype <chap-quickstart-sec-create-vp>`

The examples within the Examples repository utilize :ref:`SimBricks Cloud version <sec-architecture>`.
To run them as-is, you will need access SimBricks Demo Backend (or your own if already present).

Do get access to SimBricks Demo Backend, start by `registering for the SimBricks Demo <https://www.simbricks.io/demo/>`_.
The registration ensures you have the proper credentials to interact with the Backend. 
This is necessary to send your virtual prototypes to our Backend such that the virtual prototypes execution will be scheduled on one of our Runners.

Once You got access to our Backend, you can proceed by cloning our `Examples Repository <https://github.com/simbricks/simbricks-examples>`_:

.. code-block:: bash

  git clone git@github.com:simbricks/simbricks-examples.git
  cd simbricks-examples

After cloning and entering the examples repository, we advise to set up a `Python Virtual Environment <https://docs.python.org/3/tutorial/venv.html>`_.
You can create and activate a virtual environment as follows:

.. code-block:: bash
  
  python3 -m venv venv
  source venv/bin/activate

After the creation of your SimBricks demo account, you will need to adjust the ``simbricks-client.env`` file located in the top-level directory of the demo repository.
This is necessary to ensure your SimBricks environment is correctly configured to interact with SimBricks Backend, you need to set some environment vaiables that are used by the :ref:`SimBricks CLI and Client <sec-execution>` to communicate with the Backend.
Do the following:

- Open the ``simbricks-client.env`` file.
- Locate the line that sets the NAMESPACE variable.
- Replace ``<your demo email address>`` with the email address you used to create your demo account.

Once you’ve updated the ``simbricks-client.env`` file, you need to source the simbricks-client.env file in order to set the necessary environment variables.
This can simply be done by running the following command:

.. code-block:: bash

  source simbricks-client.env 

The last required setup step is to install required SimBricks Python Packages.
To run the examples given in the repository (or your own virtual prototypes), the following SimBricks packages are required:

- ``simbricks-orchestration``: For creating virtual prototype configurations as shown in the following.
- ``simbricks-client``: For sending configurations to the SimBricks server via Python.
- ``simbricks-cli``: For managing configurations via the terminal CLI.

You can conveniently install these packages using pip and the *requirements.txt* file we provide with the examples repository:

.. code-block:: bash

  pip install -r requirements.txt

With the above steps completed, you are ready to dive into using SimBricks.

If you encounter any issues, feel free to `reach out to us directly <https://www.simbricks.io/join-slack>`_.

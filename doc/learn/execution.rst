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

.. _sec-execution:


Running Virtual Prototypes
******************************

.. tip::
  Before running virtual prototypes check out our chapter on the :ref:`sec-orchestration-framework` that allows to configure virtual prototypes using python scripts.

  Additionally you should also check out our chapter on the :ref:`SimBricks Architecture<sec-architecture>` to get a better overview over some of the concepts talked about throughout the rest of this chapter.

In this chapter we provide an overview on how to execute your SimBricks virtual prototypes, both locally and in cloud environments.

The following information assumes some familiarity with SimBricks and that you already wrote a python script configuring your virtual prototype.
Make sure this python script is ready and contains the necessary information.

Cloud
==============================

.. attention::
  Throughout this section we will assume that you already set up Runners properly in order to execute your virtual prototypes in the cloud.
  That means we assume that you are using a setup in which Runners were created and that they have the required dependencies installed.
  These respective Runners should additionally be properly tagged to match your virtual prototyping script's configuration.

.. tip::
  If you want to learn how to set up Runners and how they function check out our documentation :ref:`here <sec-runner>` and the self-hosting instructions in :ref:`sec-setup-compile`.

SimBricks cloud version comes with a hosted SimBricks Backend that serves as the central hub for managing and executing virtual prototype simulations.
Therefore, once users specified their virtual prototypes through our python Orchestration Framework for Virtual Prototypes, users can submit those to the Backend (along with outputs and results) where they are stored, ensuring these can be retrieved at any time in the future.

Further will the Backend schedule virtual prototype execution :ref:`Runs <sec-execution-cloud-runs>` on Runners provided by users ensuring seamless resource sharing across multiple users of the same organization.

Users interact with the Backend through SimBricks :ref:`Command-Line Interface (CLI) <sec-execution-cloud-cli>` or directly in python through the :ref:`Client Library <sec-execution-cloud-client-lib>`.

.. _sec-execution-cloud-runs:

Runs
------------------------------

SimBricks Cloud introduces the concept of Runs, a foundational feature that simplifies and structures the execution of virtual prototypes defined through user-submitted configurations.
A Run encapsulates the lifecycle of a single execution instance of one of your virtual prototypes and is managed by the SimBricks backend.

That means a Run represents the execution of a virtual prototype which in turn is defined by the System-, Simulation- and Instantiation Configuration.
Once these configurations are submitted to the SimBricks Backend by a user, they can use those stored configurations to create Runs.
A Run will then encapsulate those configurations for executing the virtual prototype.

The Backend will automatically schedule available Runs (i.e. once the user created a Run or multiple Runs in the Backend) for execution.
During scheduling, the Backend will consider multiple factors:

- Availability: There must be enough Runners available to execute virtual prototypes. Especially in scenarios where the execution shall be distributed across multiple machines.
- Resources: To execute a virtual prototype (or a part thereof) on a Runner, enough computational resources must still be available on that Runner for execution.
- Tags: The backend matches Runner tags against the ``runner_tags`` specified on the Fragments of the Instantiation-Configuration to ensure Runs are executed by Runners with the appropriate tags.

If the necessary resources or tags are not available, the Run is queued until suitable Runners are accessible.

The creation and execution of a Run will not modify or alter the submitted System-, Simulation- and Instantiation Configurations.
Instead, the Run establishes the necessary connections between these configurations and the output data generated during its execution.
This ensures that the original configurations remain unchanged, allowing users to reuse them for additional Runs while maintaining a clear link to the results and logs associated with each specific execution i.e. Run.

.. _sec-execution-cloud-cli:

CLI
------------------------------------------

The CLI i.e. the ``simbricks-cli`` package provides a command-line interface for managing SimBricks virtual prototypes.
That means either sending them to or managing virtual prototypes already stored in the SimBricks Backend.

.. hint::
  You can simply install the CLI package by running ``pip install simbricks-cli``.

It is ideal when working in a terminal environment if a lightweight way to interact with the SimBricks Backend is needed.

Through the CLI you can:

- Submit Instantiation Configurations for execution:

  .. code-block:: bash

    simbricks-cli runs submit <path to your virtual prototype python script>

  Note that in order to submit a virtual prototype python script to the backend via the CLI, it must declare a module-level list called ``instantiations``.
  You can also directly follow the execution's output by passing ``--follow``.
  In case submitting your virtual prototype was successful, you should be able to see output that looks similar to the following:

  .. code-block:: console

    $ simbricks-cli runs submit <path to your virtual prototype python script>
                          Run
      --------------------------------------------
      | id | instantiation_id | state            |
      --------------------------------------------
      | 10 | 10               | RunState.SPAWNED |
      --------------------------------------------

  Alternatively users can also create a Run from an existing Instantiation Configuration that they submitted beforehand:

  .. code-block:: bash

    simbricks-cli runs create <id of the instantiation configuration>

- Assuming the execution of a virtual prototype already started. Then, in case one wants to follow the output created by that execution, it's easy to do so:

  .. code-block:: bash

    simbricks-cli runs follow <id of the run to follow>

  When following an active Run you should be able to see output that looks similar to the following (exact paths depend on the Runner's environment):

  .. code-block:: console

    [host.QemuSim-25] Formatting '/wrk/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/imgs/2_hdcopy.qcow2', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=42949672960 backing_file=/global_input/images/base/base backing_fmt=qcow2 lazy_refcounts=off refcount_bits=16
    [host.QemuSim-25] prepare command exited with code 0
    [host.QemuSim-26] Formatting '/wrk/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/imgs/10_hdcopy.qcow2', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=42949672960 backing_file=/global_input/images/base/base backing_fmt=qcow2 lazy_refcounts=off refcount_bits=16
    [host.QemuSim-26] prepare command exited with code 0
    [net.SwitchNet-29] Switch connecting to: /wrk/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/shm/eth-5.21.20
    [net.SwitchNet-29] Switch connecting to: /wrk/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/shm/eth-13.23.22
    [host.QemuSim-25] qemu-system-x86_64: warning: host doesn't support requested feature: CPUID.07H:EBX.hle [bit 4]
    [host.QemuSim-25] qemu-system-x86_64: warning: host doesn't support requested feature: CPUID.07H:EBX.rtm [bit 11]
    [host.QemuSim-25] Wrong EFI loader signature.
    [host.QemuSim-25] early console in extract_kernel
    ...


- View Runs that are currently stored on the server along their status:

  .. code-block:: bash

    simbricks-cli runs ls


.. hint::
  SimBricks CLI does offer more commands which allow users to interact with SimBricks backend for managing virtual prototypes and their execution.
  For a complete list check out :ref:`references <sec-cli-ref>`.


.. _sec-execution-cloud-client-lib:

Client Library
------------------------------------

The Client Library i.e. the ``simbricks-client`` package is used for interacting with the SimBricks Backend and implements its API.
It provides the interface i.e. python functions to:

- Upload virtual prototype configurations. That means it offers functions to send :ref:`System-, Simulation-, and Instantiation-Configurations <sec-orchestration-framework>` to the SimBricks Backend in order to store those there.

  Users can upload their Python simulation scripts and related configurations to the cloud.
- Manage Simulations: It allows users to create, stop, monitor and alter the execution of virtual prototypes through Runs.
- Retrieve Results: After a simulation is complete, users can download logs and output files for analysis.


.. hint::
  You can simply install the client library by running ``pip install simbricks-client``.

This package is particularly useful if users want to interact with SimBricks virtual prototypes in python directly. This can e.g. be very useful when integrating SimBricks into your CI/CD setup.

Through the Client Library you can:

- extend the experiment script to send the virtual prototype through the python API to the SimBricks Backend and follow its console output:

  .. code-block:: python

    import asyncio
    from simbricks.client.opus import base as opus_base

    ...
    syst = system.System()
    ...
    sim = simulation.Simulation("My-very-first-test-simulation", syst)
    ...
    instance = instantiation.Instantiation(sim)
    ...

    async def main():
        run_id = await opus_base.create_run(instance)
        line_gen = opus_base.ConsoleLineGenerator(run_id=run_id, follow=True)
        async for _, line in line_gen.generate_lines():
            print(line)

    asyncio.run(main())

- re-submit script: submit via python script itself using the api:

  .. code-block:: bash

    python3 my-simple-experiment-verbose.py

.. hint::
  If you want to have a closer look at the functions offered by our python client library check out its reference :ref:`here <sec-client-ref>`.
  A complete example of submitting runs and processing their results programmatically (including plotting) can be found in the ``prog-api-demo`` directory of the examples repository.

On-Premise
==============================

.. attention::
  The SimBricks on-premise version for local execution is designed to provide a lightweight solution for running simulations on a single machine and is **primarily meant to facilitate testing, debugging**, and running very small simulations.
  Compared to the cloud offering it comes with some limitations and a reduced feature set (e.g. no distributed simulations) and generally limited support.

It is also possible to run SimBricks virtual prototypes locally without a cloud setup or Runners.

For this SimBricks ships the ``simbricks-local`` python package that comes with a command line tool to execute simulations.
You can check that it is installed by invoking ``simbricks-run --help``. In that case you should see output similar to the following:

.. code-block::

  usage: simbricks-run [-h] [--list] [--filter PATTERN [PATTERN ...]] [--runs N] [--firstrun N] [--force] [--verbose] [--pcap] [--profile-int S] [--global-input-dir DIR] [--workdir DIR] [--parallel] [--cores N] [--mem N] EXP [EXP ...]

  positional arguments:
    EXP                   Python modules to load the experiments from

  options:
    -h, --help            show this help message and exit
    --list                List available experiment names
    --filter PATTERN [PATTERN ...]
                          Only run experiments matching the given Unix shell style patterns
    --runs N              Number of repetition of each experiment
    --firstrun N          ID for first run
    --force               Run experiments even if output already exists (overwrites output)
    --verbose             Verbose output, for example, print component simulators' output
    --pcap                Dump pcap file (if supported by component simulator)
    --profile-int S       Enable periodic sigusr1 to each simulator every S seconds.

  Environment:
    --global-input-dir DIR
                          Global input directory
    --workdir DIR         Work directory base

  Parallel Runtime:
    --parallel            Use parallel instead of sequential runtime
    --cores N             Number of cores to use for parallel runs
    --mem N               Memory limit for parallel runs (in MB)

Having it installed, users can simply execute their virtual prototypes by running the following:

.. code-block:: bash

  simbricks-run --verbose --global-input-dir <dir with disk images> <path to your virtual prototype python script>

This command will cause SimBricks to run your virtual prototype locally.

Local execution requires the simulators used by your virtual prototype and their dependencies to
be available locally: install the respective ``simbricks-*-bin`` conda packages from the SimBricks
conda channel (see :ref:`sec-conda-packages`), and provide a global input directory containing the
disk images your script references (see :ref:`sec-disk-images`).
Alternatively, you can run inside the pre-built ``simbricks/simbricks-executor`` Docker container,
which has both already set up (see :ref:`sec-docker-images`).

.. hint::
  You can simply install the SimBricks package for local execution by running ``pip install simbricks-local``, or install it from the SimBricks conda channel together with the simulators.

All output is collected in a JSON file (``<workdir>/.../output/out.json``), which allows easy post-processing afterwards.
Output files generated through local execution will be placed in a local folder (``./out/`` by default, configurable via ``--workdir``) that users can investigate to extract data from the execution.

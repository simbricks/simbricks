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

###################################
SimBricks Orchestration
###################################

******************************
Concepts
******************************

Experiments
===========

Runs
====

Component Simulators
====================

Node Configuration
==================

Application Configuration
-------------------------


******************************
Running Experiments
******************************

Command Line
====================

.. code-block:: bash

   usage: simbricks-run [-h] [--filter PATTERN [PATTERN ...]] [--pickled] [--runs N]
               [--firstrun N] [--force] [--verbose] [--pcap] [--repo DIR]
               [--workdir DIR] [--outdir DIR] [--cpdir DIR] [--parallel]
               [--cores N] [--mem N] [--slurm] [--slurmdir DIR]
               EXP [EXP ...]

Positional arguments
--------------------

   *  ``EXP``

      An experiment file to run.

Optional arguments
------------------

   *  `` -h, --help``

      show this help message and exit.
   
   * `` --filter PATTERN [PATTERN ...] ``
      Pattern to match experiment names against

Environment
-----------


******************************
Images
******************************


******************************
Distributed Simulations
******************************


******************************
Slurm
******************************

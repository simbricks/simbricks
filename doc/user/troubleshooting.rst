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
Troubleshooting
###################################

************************************
Is my Simulation Stuck or just Slow?
************************************

It is possible to check the current timestamp of individual component
simulators. If the timestamp of one of them isn't advancing, then the simulation
is stuck. To make one of our already implemented component simulators output its
current timestamp, send a USR1 signal, for example, by invoking ``kill -s USR1
<insert_pid_of_simulator>``.

When the orchestration framework is running in verbose mode (see
:ref:`sec-command-line`), the current timestamp is visible in the terminal where
you invoked the SimBricks orchestration framework to execute your experiment.
Otherwise, you can interrupt the execution via CTRL+C to produce the output JSON
for the experiment. All component simulator's output is logged there.

************************************
Understanding Simulation Performance
************************************


.. _sec-troubleshoot-getting-help:

******************************
Getting Help
******************************
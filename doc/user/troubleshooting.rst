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
Troubleshooting / FAQ
###################################

This is a collection of common troubleshooting tips and answers to frequently
asked questions.

.. _sec-troubleshoot-getting-help:

******************************
Getting Help
******************************

We love to hear from you. If you have questions, want to discuss an idea, or
encountered issues while using SimBricks, we are available on `Slack
<https://join.slack.com/t/simbricks/shared_invite/zt-16y96155y-xspnVcm18EUkbUHDcSVonA>`_
for quick answers and interactive discussions. If you find bugs or want to
request a feature, feel free to open an `issue on GitHub
<https://github.com/simbricks/simbricks/issues>`_.

*****************************************
Error Opening images/output-base/base.raw
*****************************************

Some of our host simulators, e.g., gem5 and Simics, require raw disk images. If
these aren't available, you will see the error in the title or something
similar. If you use our Docker images, we deliberately remove these since Docker
doesn't handle large, sparse files well, which leads to large Docker image
sizes. We include disk images in the qcow format though, which can easily be
converted to raw. To do so, just run the following (requires QEMU to be built
first):

.. code-block:: bash

  $ make convert-images-raw

If you are not using the provided docker containers, you might need to build the
qcow images by running the following (again, requires QEMU to be built first):

.. code-block:: bash

  $ make build-images-min

************************************
Is My Simulation Stuck or Just Slow?
************************************

It is possible to check the current timestamp of individual component
simulators. If the timestamp of one of them isn't advancing, then the simulation
is stuck. To make one of our already implemented component simulators output its
current timestamp, send a USR1 signal, for example, by invoking ``kill -s USR1
<insert_pid_of_simulator>``.

When the orchestration framework is running in verbose mode (see
:ref:`sec-command-line`), the current timestamp is visible in the terminal in
which you invoked ``experiments/run.py``. Otherwise, you can interrupt/stop the
execution via Ctrl+C to produce the output JSON for the experiment. All
component simulator's output is logged there.

************************************
Understanding Simulation Performance
************************************

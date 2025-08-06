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

.. _chap-quickstart-sec-executing-vp:

Executing Your First Virtual Prototype
************************************************************************

Now that we created our first virtual prototype we can execute it.

For this we make use of SimBricks CLI i.e. the ``simbricks-cli`` package.
This package provides a command-line interface for managing SimBricks virtual prototypes.
It is ideal when working in a terminal environment if a lightweight way to interact with the SimBricks Backend is needed.

In our case we can use ot to send the virtual prototype we just created to the SImBRicks Backend for execution.
For this we save our virtual prototype script in a file called ``my-simple-experiment.py``. 

Then we use we submit the script to the Backend and follow its execution.
In case of success you should sess output like the following:

.. code-block:: console

  $ simbricks-cli runs submit --follow my-simple-experiment.py 
                        Run                     
    ┏━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
    ┃ id ┃ instantiation_id ┃ state            ┃
    ┡━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
    │ 10 │ 10               │ RunState.PENDING │
    └────┴──────────────────┴──────────────────┘
    [host.QemuSim-25] Formatting '/workspaces/simbricks_docker/runner-work/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/imgs/hdcopy.2', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=42949672960 
    backing_file=/workspaces/simbricks_docker/images/output-base/base backing_fmt=qcow2 lazy_refcounts=off refcount_bits=16
    [host.QemuSim-25] prepare command exited with code 0
    [host.QemuSim-26] Formatting '/workspaces/simbricks_docker/runner-work/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/imgs/hdcopy.10', fmt=qcow2 cluster_size=65536 extended_l2=off compression_type=zlib size=42949672960 
    backing_file=/workspaces/simbricks_docker/images/output-base/base backing_fmt=qcow2 lazy_refcounts=off refcount_bits=16
    [host.QemuSim-26] prepare command exited with code 0
    [net.SwitchNet-29] Switch connecting to: /workspaces/simbricks_docker/runner-work/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/shm/eth-5.21.20
    [net.SwitchNet-29] Switch connecting to: /workspaces/simbricks_docker/runner-work/run-10-767b3eb9-f93f-495a-80ee-d9754981d7aa/tmp/shm/eth-13.23.22
    [host.QemuSim-25] qemu-system-x86_64: warning: host doesn't support requested feature: CPUID.07H:EBX.hle [bit 4]
    ...

With that you executed your first SimBricks virtual prototype.

.. hint::
  When executing the the command above you might be promted to authenticate yourself:

  .. code-block:: console
    
    Please visit https://auth.simbricks.io/realms/SimBricks/device in the browser
    There, enter the code: GZPU-FEAP
    Waiting...

  In that case visit the given link and enter the code above.
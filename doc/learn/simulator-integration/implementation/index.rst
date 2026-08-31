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

.. _sec-simulator-integration-implementation:

Implementation
==============================

.. tip::
  If you're new to SimBricks and have not already read it you might want to check out our documentation :ref:`background on Adapters <sec-simulator-integration-background>`.

As we have seen :ref:`before <sec-simulator-integration-background>` does SimBricks enable the modular connection and synchronization of component simulators to create virtual prototypes.

Now we will have a look at the practical steps one has to take in order to integrate a component simulator into the SimBricks platform for the first time.
We can divide this integration process roughly into two steps:

1. **Adapter Implementation:** We discussed that SimBricks defines standardized interfaces and achieves simulator integration by the implementation of an Adapter between the SimBricks interface
   and the simulator's internal abstractions.

2. **Orchestration Framework Integration:** Once this adapter is implemented the respective simulator must be integrated into the SimBricks :ref:`sec-orchestration-framework`.
   This will allow users to easily make use of the integrated simulator within python scripts that are used by SimBricks to configure virtual prototypes.


Adapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Adapter required for the integration into SimBricks must use a simulator's extension API to act as a native device on one side and on the other side it must send and receive SimBricks messages to and from other Adapters.


SimBricks Interface and Message Types
"""""""""""""""""""""""""""""""""""""""""""

As we saw in the :ref:`background section <sec-simulator-integration-background>` are SimBricks interfaces designed around natural component boundaries.
For instance a PCIe interface connects a host simulator to a hardware device simulator whereas an Ethernet interface may connect a NIC simulator and a network simulator.

Understanding these interfaces and the respective message types associated with such an interface is a crucial first step in writing an Adapter.
Typically these interfaces abstract key transactions.

When **implementing an Adapter** users must either **re-use** any of the message types already supported by SimBricks or **implement their own Message Types** depending on their needs.

Lets look at an example: the SimBricks PCIe interface currently supports the following message types between host and device: ``INIT_DEV``, ``DMA_READ/WRITE/COMPLETE``, ``MMIO_READ/WRITE/COMPLETE`` and ``INTERRUPT``.

Let's look at a concrete example of these message types, namely the ``DMA_WRITE`` message that is issued when a device issue a DMA write access to the host, demonstrating how interactions are structured:

.. _sec-simulator-integration-implementation-message-type-example:
.. code-block:: C
  :caption: Example SimBricks Message-Type from SimBricks :ref:`Core Library <sec-core-lib-ref>`

  struct SimbricksProtoPcieD2HWrite {
    // message type specific / custom fields
    uint64_t req_id;
    uint64_t offset;
    uint16_t len;
    uint8_t pad[30];
    // standard fields
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
    // optional message payload
    uint8_t data[];
  }

Message types for any protocol are defined using structs specific to each type.
Like in the shown example message type, do message types across SimBricks interfaces share a common structure with the following **order**:

1. **Header:**

   * Includes type-specific fields and standard fields for synchronization and identification.

     - **Type specific** fields are in the given case the ``req_id``, ``offset`` and ``len`` field.
     - The padding (``pad``) following those fields has to be adjusted.
     - **Standard header** fields are ``timestamp``, ``pad``, and the ``own_type`` field.

   * Has to be cache-line-sized.

2. **Payload (optional):**

   * Variable-length, used for transmitting data.

Each message type is identified by a unique integer stored in the ``own_type`` field.

.. note::
    The header always starts with message type specific fields, and ends with standard SimBricks message fields for synchronization and message identification.

.. warning::
    Users must avoid conflicts with fields in the base SimBricks protocol when implementing custom message types.

The total message size is determined by channel parameters configured at runtime.
Additionally is the shown example protocol (PCIe) asymmetric, requiring distinct message types for the Host-to-device (H2D) and the device-to-host (D2H) sending directions.
Other protocols, like the Ethernet protocol, are symmetric. In that case both sides send packets in a send-and-forget manner, simplifying the implementation as not as many distinct message types are needed.

Adapters interpret these incoming messages, translating them into actions within the simulator.
Similarly, they send these messages to communicate events back to their peers.

.. seealso::
    For more examples of such message types check out our :ref:`Core Lib References <sec-core-lib-ref>`


Actual Adapter Implementation
"""""""""""""""""""""""""""""""""""""""""""

Once the Adapters interface is determined and the respective message types are implemented, the next step is to actually implement the Adapter logic.
Every Adapter implementation involves three main steps: :ref:`adapter-init`, the :ref:`adapter-handling-messages` as well as :ref:`adapter-poll-sync`.

For illustration we will have a look at the Adapter Code used by SimBricks to integrate the :verilator:`\ ` simulation of the :corundum:`\ ` .
This is also an example for an Adapter that implements both, the SimBricks PCIe interface as well as the SimBricks ethernet interface and would thus in a virtual prototype connect to both, a host and a network.

.. important::
  We only show the part of the Adapter that is specific to SimBricks and it's :ref:`Core Library <sec-core-lib-ref>`.

  In between the functions and the functions whose implementation is not shown in the following example its the programmers responsibility to
  interact with the respective simulator. That means there one would need to deal with a simulator's internal abstractions through the API they
  expose to trigger actions or schedule actions depending on the messages received through functions as shown in the example.

  These internal abstractions depend on the actual simulator. If you want to get an idea of concrete examples on how to do this check out :ref:`some of our Adapter examples <adapter-examples>`.

.. _adapter-init:

Initialization
--------------------------------------------

* Establish connections with peer simulators.

  - For this we use the SimBricks library helpers to establish communication channels.

* Exchange initial protocol-specific messages.

  - Example: In PCIe, the device simulator sends device information (e.g., BARs, interrupts) to the host.

* In :numref:`code-adapter-initialize` you can see the initialization code from our Corundum Verilator Adapter.

.. note::

  All time intervals in ``SimbricksBaseIfParams`` (``link_latency``, ``sync_interval``) are given in
  **picoseconds**. The same holds for the time intervals in the SimBricks parameters url that the
  orchestration framework passes to a simulator (``:latency=XX:sync_interval=XX``), which are plain
  decimal picosecond values without a unit suffix. Adapters using
  ``SimbricksParametersParse``/``SimbricksParametersEstablish`` must therefore not rescale the parsed
  values.

.. _code-adapter-initialize:

.. code-block:: C++
  :linenos:
  :caption: SimBricks :corundum-verilator-adapter:`\ ` Initialization Code.

  ...

  int main(int argc, char *argv[]) {

    ...

    struct SimbricksBaseIfParams netParams;
    struct SimbricksBaseIfParams pcieParams;

    SimbricksNetIfDefaultParams(&netParams);
    SimbricksPcieIfDefaultParams(&pcieParams);

    ...

    struct SimbricksProtoPcieDevIntro di;
    memset(&di, 0, sizeof(di));

    di.bars[0].len = 1 << 24;
    di.bars[0].flags = SIMBRICKS_PROTO_PCIE_BAR_64;

    di.pci_vendor_id = 0x5543;
    di.pci_device_id = 0x1001;

    ...

    pcieParams.sock_path = argv[1];
    netParams.sock_path = argv[2];

    if (SimbricksNicIfInit(&nicif, argv[3], &netParams, &pcieParams, &di)) {
      return EXIT_FAILURE;
    }

    ...

  }


.. _adapter-handling-messages:

Handling Incoming Messages
--------------------------------------------

* Poll the incoming queue for messages.
* Interpret the SimBricks messages and call corresponding simulator functions to process events.
* Message handling typically involves a switch statement to manage different message types.

  - Example: Handling an MMIO_READ message involves retrieving the corresponding memory-mapped data and responding.

* In :numref:`code-adapter-handling-incoming` you can see the example code for handling incoming messages from our Corundum Verilator Adapter.

  - The main simulation loop polls the incoming queue for each channel.
  - You can see that in this Adapter two poll functions (``poll_h2d``, ``poll_n2d``) are used. One to handle messages coming from the host interface and another to handle message received on the ethernet interface.
  - Each of these function triggers different actions in the simulator (in this case Verilator) depending on the Message Type they receive from their respective interface. An example of how this might be handled
    is shown in the ``h2d_read`` function that will read the received message and triggers the mmio read by interacting with Verilators top level module.

.. _code-adapter-handling-incoming:

.. code-block:: C++
  :linenos:
  :caption: SimBricks :corundum-verilator-adapter:`\ ` Code Handling Incoming Messages.

  ...

  static void h2d_read(MMIOInterface &mmio,
                     volatile struct SimbricksProtoPcieH2DRead *read) {
    if (read->offset < 0x80000) {
      volatile union SimbricksProtoPcieD2H *msg = d2h_alloc();
      volatile struct SimbricksProtoPcieD2HReadcomp *rc;

      ...

      rc = &msg->readcomp;
      memset((void *)rc->data, 0, read->len);
      uint64_t val = csr_read(read->offset);
      memcpy((void *)rc->data, &val, read->len);
      rc->req_id = read->req_id;

      SimbricksPcieIfD2HOutSend(&nicif.pcie, msg,
                                SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP);
    } else {
      mmio.issueRead(read->req_id, read->offset, read->len);
    }
  }

  ...

  static void poll_h2d(MMIOInterface &mmio) {
    volatile union SimbricksProtoPcieH2D *msg =
        SimbricksPcieIfH2DInPoll(&nicif.pcie, main_time);
    uint8_t t;

    if (msg == NULL)
      return;

    t = SimbricksPcieIfH2DInType(&nicif.pcie, msg);

    // std::cerr << "poll_h2d: polled type=" << (int) t << std::endl;
    switch (t) {
      case SIMBRICKS_PROTO_PCIE_H2D_MSG_READ:
        h2d_read(mmio, &msg->read);
        break;

      case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE:
        h2d_write(mmio, &msg->write);
        break;

      case SIMBRICKS_PROTO_PCIE_H2D_MSG_READCOMP:
        h2d_readcomp(&msg->readcomp);
        break;

      case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITECOMP:
        h2d_writecomp(&msg->writecomp);
        break;

      case SIMBRICKS_PROTO_PCIE_H2D_MSG_DEVCTRL:
        break;

      case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
        break;

      case SIMBRICKS_PROTO_MSG_TYPE_TERMINATE:
        std::cerr << "poll_h2d: peer terminated" << std::endl;
        pci_terminated = true;
        break;

      default:
        std::cerr << "poll_h2d: unsupported type=" << t << std::endl;
    }

    SimbricksPcieIfH2DInDone(&nicif.pcie, msg);
  }

  ...

  static void poll_n2d(EthernetRx &rx) {
    volatile union SimbricksProtoNetMsg *msg =
        SimbricksNetIfInPoll(&nicif.net, main_time);
    uint8_t t;

    if (msg == NULL)
      return;

    t = SimbricksNetIfInType(&nicif.net, msg);
    switch (t) {
      case SIMBRICKS_PROTO_NET_MSG_PACKET:
        n2d_recv(rx, &msg->packet);
        break;

      case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
        break;

      default:
        std::cerr << "poll_n2d: unsupported type=" << t << std::endl;
    }

    SimbricksNetIfInDone(&nicif.net, msg);
  }

  ...

  int main(int argc, char *argv[]) {

    ...

    do {
      poll_h2d(mmio);
      poll_n2d(rx);
    } while

    ...

  }

.. _adapter-poll-sync:

Polling and Synchronization
--------------------------------------------

* Poll messages and synchronize the simulator's clock:

  - Basic simulators: Poll queues, advancing time based on the next message timestamp.
  - Complex event-based simulators: Schedule an event to process the next message and re-schedule after processing.

* Ensure the simulation clock never progresses ahead of incoming messages.
* Periodically send dummy messages when no data messages are available to ensure the peer simulator can progress.
* In :numref:`code-adapter-poll-sync` you can see example code from our Corundum Verilator adapter that handles polling and synchronization.

.. _code-adapter-poll-sync:

.. code-block:: C++
  :linenos:
  :caption: SimBricks :corundum-verilator-adapter:`\ ` Polling and Synchronization Code.

  ...

  int main(int argc, char *argv[]) {

    ...

    struct SimbricksBaseIfParams netParams;
    struct SimbricksBaseIfParams pcieParams;

    ...

    SimbricksNetIfDefaultParams(&netParams);
    SimbricksPcieIfDefaultParams(&pcieParams);

    ...

    if (argc >= 6)
      main_time = strtoull(argv[5], NULL, 0);
    if (argc >= 7)
      netParams.sync_interval = pcieParams.sync_interval =
          strtoull(argv[6], NULL, 0);
    if (argc >= 8)
      pcieParams.link_latency = strtoull(argv[7], NULL, 0);
    if (argc >= 9)
      netParams.link_latency = strtoull(argv[8], NULL, 0);
    if (argc >= 10)
      clock_period = 1000000ULL / strtoull(argv[9], NULL, 0);

    ...

    int sync_pci = SimbricksBaseIfSyncEnabled(&nicif.pcie.base);
    int sync_eth = SimbricksBaseIfSyncEnabled(&nicif.net.base);

    ...

    top->clk = !top->clk;
    top->eval();

    ...

    while (!exiting) {
      int done;
      do {
        done = 1;
        if (SimbricksPcieIfD2HOutSync(&nicif.pcie, main_time) < 0) {
          ...
        }
        if (SimbricksNetIfOutSync(&nicif.net, main_time) < 0) {
          ...
        }
      } while (!done);

      do {
        ...
      } while (
          !exiting &&
          ((sync_pci &&
            SimbricksPcieIfH2DInTimestamp(&nicif.pcie) <= main_time) ||
          (sync_eth && SimbricksNetIfInTimestamp(&nicif.net) <= main_time)));

      /* falling edge */
      top->clk = !top->clk;
      main_time += clock_period / 2;
      top->eval();

      // adjust simulator state
      ...

      /* raising edge */
      top->clk = !top->clk;
      main_time += clock_period / 2;

      ...

      top->eval();
    }
    ...
  }

.. _adapter-examples:

.. admonition:: Here you will find more Adapter implementations of already supported simulators.

    In case you want to have a look at some more actual Adapter code, have a look at one of the following Adapters:

    * **Host:** :gem5-adapter:`\ `
    * **PCI Device:** :corundum-verilator-adapter:`\ ` , :jped-decoder-adapter:`\ `
    * **Network:** :ns3-adapter:`\ `





Orchestration Framework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the Adapter is implemented and the simulator builds, the last step is to make the simulator
usable from virtual prototype scripts. In the modular SimBricks layout this means providing two
small Python packages in your component repository that plug into the shared
``simbricks.components.*`` namespace (see :ref:`sec-orchestration-framework-components`):

1. **System components** (``simbricks.components.<x>.system``, optional): concrete component
   classes for the System Configuration that subclass the generic classes from
   ``simbricks.orchestration.system``. For a NIC this is typically a subclass of
   ``SimplePCIeNIC`` plus, if a driver needs to be loaded in the guest, a host subclass that
   appends the driver to the host's driver list. As an example, the i40e component defines:

   .. code-block:: python

     from simbricks.orchestration.system import nic
     from simbricks.orchestration.system.host import base as sys_host


     class IntelI40eNIC(nic.SimplePCIeNIC):
         ...


     class I40ELinuxHost(sys_host.LinuxHost):
         def __init__(self, sys) -> None:
             super().__init__(sys)
             self.drivers.append("i40e")

2. **A simulator class** (``simbricks.components.<x>.simulation``): a subclass of one of the
   simulator base classes in ``simbricks.orchestration.simulation`` (``HostSim``, ``NICSim``,
   ``PCIDevSim``, ``NetSim``, or plain ``Simulator``) that defines which executable to run and how
   to construct its command line. The base class handles socket setup and synchronization
   parameters; you mainly pass the executable name and implement/extend ``run_cmd()``:

   .. code-block:: python

     from simbricks.orchestration.simulation import pcidev


     class I40eNicSim(pcidev.NICSim):
         def __init__(self, simulation) -> None:
             super().__init__(simulation=simulation, executable="simb_i40e_bm")

         def run_cmd(self, inst) -> str:
             cmd = self.basic_run_cmd(inst)
             ...
             return cmd

   The ``executable`` is resolved through ``$PATH`` at execution time — by convention it is
   installed under exactly this name by the component's binary conda package (e.g.
   ``simb_i40e_bm`` by ``simbricks-i40e-sim-bm-bin``). Where a simulator needs additional
   installed files (e.g. gem5's config scripts), the simulator class resolves them relative to
   ``$CONDA_PREFIX`` (or a dedicated override environment variable).

With these classes in place, users select your simulator in their Simulation Configuration just
like any built-in one, e.g. ``compmap={i40e_sys.IntelI40eNIC: i40e_sim.I40eNicSim, ...}``.

How to lay out the component repository and package everything up as conda packages is described
in :ref:`sec-simulator-integration-packaging`.

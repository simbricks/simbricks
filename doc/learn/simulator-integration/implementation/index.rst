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


.. _sec-simulator-integration-implementation:

Implementation
==============================

As we have seen :ref:`before <sec-simulator-integration-background>` does SimBricks enable the modular connectiion and synchronization of component simulators to create virtual prototypes.

Now we will have a look at the practical steps one has to take in order to integrate a component simulator into the SimBricks platform for the first time.
We can divide this integration process roughly into two steps:

1. **Adapter Implementation:** We discussed that SimBricks defines standardized interfaces and achieves simulator integration by the implementation of an Adapter between the SimBricks interface
   and the simulators internal abstractions.

2. **Orchestration Framework Integration:** Once this adapter is implemented the respective simulator must be integrated into the SimBricks :ref:`sec-orchestration-framework`.
   This will allow users to easily make use of the integrated simulator within python scripts that are used by SimBricks to configure virtual prototypes.


Adapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Adapter required for the integratoin into SimBricks must use a simulator’s extension API to act as a native device on one side and on the other side it must send and receive SimBricks messages to and from other Adapters.


SimBricks Interface and Message Types
"""""""""""""""""""""""""""""""""""""""""""

As we saw in the :ref:`background section <sec-simulator-integration-background>` are SimBricks interfaces are designed around natural component boundaries. 
For instance a PCIe interface connects a host simulator to a hardware device simulator whereas an Ethernet interface may connect a NIC simulator and a network simulator.

Understanding these interfaces and the respective message types associated with such an interface is a crucial first step in writing an Adapter.
Typically these interfaces abstract key transactions. 

For example, the SimBricks PCIe interface currently supports the following message types between host and device: ``INIT_DEV``, ``DMA_READ/WRITE/COMPLETE``, ``MMIO_READ/WRITE/COMPLETE`` and ``INTERRUPT``.

Let's look at a concrete example of these message types, namely the ``DMA_WRITE`` message that is issued when a device issue a DMA write access to the host, demonstrating how interactions are structured:

.. doxygenstruct:: SimbricksProtoPcieD2HWrite
   :project: simbricks
   :members:
   :protected-members:
   :private-members:
   :undoc-members:
   :outline:

Message types for any protocol are defined using structures (struct) specific to each type.
Like in the case of the shown message type, do these message types across SimBricks interfaces share a common structure in the following order:

1. **Header:**
  
   * Includes type-specific fields and standard fields for synchronization and identification.
    
     - **Type specific** are in the given case the ``req_id``, ``offset`` and ``len`` field.
     - The padding following those fields has to be adjusted. 
     - **Standard header** fields are ``timestamp``, ``pad``, and the ``own_type`` field.

   * Has to be ache-line-sized.

2. **Payload (optional):**
   
   * Variable-length, used for transmitting data.

Each message type is identified by a unique integer stored in the ``own_type`` field.

.. note::
    The header always starts with message type specific fields, and ends with standard SimBricks message fields for synchronization and message identification.

.. warning::
    Care must be taken to avoid conflicts with fields in the base SimBricks protocol.

The total message size is determined by channel parameters configured at runtime.
Additionally is the shown example protocol (PCIe) asymmetric, requiring distinct message types for the Host-to-device (H2D) and the device-to-host (D2H) sending directions.
Other protocols, like the Ethernet protocol, are symmetric. In that case both sides send packets in a send-and-forget manner, simplifying the implementation as not as many distinct message types are needed.

Adapters interpret these incoming messages, translating them into actions within the simulator.
Similarly, they send these messages to communicate events back to their peers.

.. seealso::
    For more exaples of such message types check out our :ref:`Core Lib References <sec-core-lib-ref>`


Actual Adapter Implementation
"""""""""""""""""""""""""""""""""""""""""""

Once the Adapters interface is determined, the next step is to actually implement an Adapter.
For illustration, consider integrating a PCIe device.
The actual Adapter implementation involves three main components:

1. **Initialization**

   * Establish connections with peer simulators.
   * Exchange initial protocol-specific messages.
     
     - Example: In PCIe, the device simulator sends device information (e.g., BARs, interrupts) to the host.
    
   * Use SimBricks library helpers to establish communication channels.

2. **Handling Incoming Messages**
   
   * Poll the incoming queue for messages.
   * Interpret the SimBricks messages and call corresponding simulator functions to process events.
   * Message handling typically involves a switch statement to manage different message types. For instance:
     
     - Handling an MMIO_READ message involves retrieving the corresponding memory-mapped data and responding.

3. **Polling and Synchronization**

   * Poll messages and synchronize the simulator's clock: 
     
     - Basic simulators: Poll queues, advancing time based on the next message timestamp.
     - Complex event-based simulators: Schedule an event to process the next message and re-schedule after processing.

   * Ensure the simulation clock never progresses ahead of incoming messages.
   * Periodically send dummy messages when no data messages are available to ensure the peer simulator can progress.



.. admonition:: Here you can find some Adapter implementations of already supported simulators.

    Host
        `gem5 <https://github.com/simbricks/gem5/blob/2c500a6a7527a1305e1a8e03f53ea11e90b71b73/src/simbricks/base.hh>`_

    PCI Device
        `Corundum NIC <https://github.com/simbricks/simbricks/blob/57eeed65e91a467ce745b3880347f978c57e3beb/sims/nic/corundum/corundum_verilator.cc>`_

    Network
        `ns3 <https://github.com/simbricks/ns-3/blob/1ce6dca3b68da284eb0ce4a47f7790d0a0e745d8/src/simbricks/model/simbricks-base.cc>`_


..
 TODO: BETTER EXAMPLES IN THIS SECTION


..
    Once we determine the interface, we can begin writing an adapter.
    For illustration, we use an example from our repo where we integrate a matrix multiplication accelerator as a PCIe device.
    At a high level, implementing an adapter involves three key components:
    Adapter initialization
    Handing incoming messages
    Implementing polling & synchronization

    Adapter Initialization
    During startup, the adapter has to establish connections with its peer simulators. 
    This also includes an initial protocol-specific welcome message.
    In the case of PCIe, the device simulator will send the device information message to the host during this process, including device identification information, BARs, supported interrupts, etc..
    The SimBricks library provides helpers to establish connected channels.
    
    Handling Incoming Messages
    The main simulation loop polls the incoming queue for each channel.
    Once a message is ready for processing, the adapter interprets the message from the SimBricks channel and calls the corresponding internal simulator functions to process the event.
    This function typically boils down to a switch case to handle each message type.
    Below is an example from our Matrix Multiplication accelerator for handling an MMIO_READ message received from the PCIe channel.

    Implementing Polling & Synchronization
    Once message handling is ready, the next step is implement the channel polling and synchronization logic.
    The details here heavily depend on the specific simulator’s mechanics.
    A basic simulation model as in the example above might simply poll for messages in the simulation loop, and advance the simulation time according to the minimal next message timestamp for synchronization (see our recent synchronization post).
    For more complex discrete event-based simulator with scheduled event queues, the logic is slightly more complex.
    At a very high level, the adapter schedules an event for processing the next message, and at the end of this handler polls for the next message and re-schedules the event (see our gem5 adapter as an example).
    This ensures that the simulator clock does not proceed ahead of the next message.
    Additionally, the simulator also needs to periodically send out dummy messages to allow its peer to progress when no data messages have been sent.

Orchestration Framework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TODO
..
    Lastly, 
    Create a simulator class that inherits from the PCI device simulator class and configure the command to run the simulator.
    With this simulator class defined in the orchestration framework, we can invoke it in the experiment script and run it alongside other components in an end-to-end environment.
    For further guidance to the simulation script, refer to our previous blog post on running a simple experiment with the orchestration framework.

..
    To make running experiments and setting up the SimBricks communication channels to other simulators convenient, add a class for the simulator in orchestration/simulators.py` that inherits either from Simulator or one of the more specialized base classes in.
    In this class, you define the command(s) to execute the simulator together with further parameters, for example, to connect to the communication channels with other simulators.
    Below is an example of what this looks like.


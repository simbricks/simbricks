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


.. _sec-simulator-integration:


Simulator Integration
******************************

SimBricks enables the creation of virtual prototypes by orchestrating, connecting and synchronizing multiple instances of already existing (or newly created)
simulators. To use them as part of the SimBricks platform, a user must integrate a respective simulator.

On this page, we provide an overview of how SimBricks connects existing simulators into an end-to-end virtual prototype. 
In the end, you should have all the required knowledge to extend SimBricks by integrating a new Simulator. 

.. note::
    In case you want to jump straight into the **implementation details**, check out the :ref:`sec-simulator-integration-implementation` section.  


Background
==============================

We begin by introducing the high-level idea for connecting existing simulators. 

In a real physical systems, different components connect through common interfaces like PCIe or Ethernet. 
For example, a PCIe device can connect to any machine with PCIe, and a modern Ethernet device does not need to know what component it connects to.

We apply the same idea to creating virtual prototypes of complex systems: the structure of the virtual prototype corresponds to the structure of the simulated system,
and we interface different component simulators at natural interfaces for the physical system as shown in :numref:`overview-inkscape`.

Similarly to the real world do many existing simulators already expose an API for extending the simulation with components or devices that attach through these interfaces.
As a result, integrating a simulator into SimBricks only requires the developer to add Adapters for the specific interfaces, and to match these up with that simulator’s internal abstractions through the API they expose.
Hence, no complicated structural changes within an simulator are needed.
This reduces the complexity of integration as only compatibility with the SimBricks interface must be ensured, rather than with all other simulators.
Therefore, an adapter for a SimBricks interface only has to be implemented once when initially integrating the simulator.

.. _overview-inkscape:
.. figure:: overview-inkscape.svg
  :width: 800

  Schematic SimBricks virtual prototype composed of multiple simulators connected through Adapters at natural interface boundaries like PCIe and Ethernet.

SimBricks approach ensures modularity and the ability to flexibly combine simulators within a virtual prototype.
Adding Adapters at common interfaces means that you can swap out one simulator for another without having to change the adapter at the other side of the
connection under the assumption that the interface doesn’t change.

Additionally does SimBricks run individual component simulators as separate independent processes.
This makes the integration of independently implemented simulators (potentially using different programming languages and incompatible simulation modes)
easy as only the SimBricks interface has to be implemented correctly as part of a simulator.

Running component simulators as separate processes enables parallelism such that a virtual prototype with more components does require additional processor
resources but does not increase execution time significantly.

Two common examples for SimBricks interfaces are PCIe and Ethernet.
A PCIe device simulator can connect any simulator implementing the PCIe host interface.
Therefore, adding a PCIe adapter to a host simulator allows to connect to any other simulator that implements a device-side PCIe adapter. 

.. note::
    This approach does work for **closed-source simulators**, given they expose the necessary extensibility / API.


.. warning::
    An important consideration when implementing the adapter is that, depending on the concrete interface, the two sides of a connection are not necessarily symmetric.
    
    This is for example the case when implementing a host-device PCIe interface within an adapter. 
    In the case of PCIe, the host can initiate BAR and PCIe config reads or writes. 
    The device, on the other hand, performs DMA and raises interrupts.


SimBricks Protocol
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The independent component simulator processes need to communicate.
The **SimBricks Protocol** defines the specifics of this interchange.

To retain loose coupling, we implement this through message-passing. 
That means the Adapters implementing a respectife interface as part of a simulator, communicate with each other through the exchange of messages as shown in :numref:`loosely-coupled-simulator-processes`.

.. _loosely-coupled-simulator-processes:
.. figure:: loosely-coupled-simulator-processes.svg
  :width: 800

  Abstract view on a virtual prototype consisting of multiple simulator instances connected through SimBricks Adapters.

When creating virtual prototypes, simulators and therefore their respective Adapters, are always connected pair-wise. 
This pairwise message-passing between simulators ensures efficiency and scalability.

A single simulator can however have multiple Adapters, each connecting to an Adapter in another simulator. 
You can see this for example in the case of the network simulator in :numref:`overview-inkscape`.

The message-passing between Adapters is handled by optimized shared memory queues. 
Through such queues, adpaters exchange SimBricks protocol messages containing information about events in a FIFO manner.

From an Adapters point of view, there is **one queue sending messages and one queue for receiving messages**, respectively.

.. note::
    Therefore, when we say Adapters are always connected pair-wise the actual connecting consists of two shared memory queues. 
    One for sending SimBricks messages from Adapter A to Adapter B and another queue for the other direction.  

Having established these queues, each Adapter polls for messages on its respective receive queue.
This minimizes message transfer overhead and ensures fast simulation times as long as every simulator runs on its own physical CPU core.

**Interface-specific protocols** and thus the exchanged messages are defined on top of the SimBricks `Base protocol <https://github.com/simbricks/simbricks/blob/main/lib/simbricks/base/proto.h#L118-L131>`_.
The Base protocol stores two important fields at fixed offsets within the header (first 64 bytes) of each message:

* own_type - An integer identifying the message type, required to correctly interpret the message when processing it later.
* timestamp - Timestamp when the event occurred. Required when synchronizing to process the event at the correct time in the receiving simulator.

These fields **must not** be changed. Apart from that the header layout can be freely customized by the interface-specific protocol a user wants to implement. 
This includes the message size which is freely configurable per interface to accommodate payloads of different size.


Synchronization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. 
    synchronization
    So far, we only covered transmitting important events in one simulator to another. In case you are just interested in functional simulation, for example, for debugging or functional testing, you can run the whole virtual testbed unsynchronized for the lowest simulation time and skip this section. In order to get sensible end-to-end measurements, however, you need to synchronize the advancement of virtual time between the simulators.
    Synchronization in the case of SimBricks means informing the connected simulator that there will be no more messages to process up to some concrete timestamp. For this, the base protocol defines a special synchronization message type. Synchronization messages are sent over the same pair of send and receive queues as the interface-specific messages. However, sending these for every tick of a simulator’s virtual clock doesn’t scale. We can use some of SimBricks’ properties to reduce their number. First, we don’t need to synchronize simulators globally. Instead, it suffices to only do so pair-wise along the connections between adapters. In particular, this means that we don’t have to synchronize simulators that aren’t directly connected.
    Furthermore, all messages are inserted into the shared memory queues in FIFO order of when their respective event occurred in the sending simulator. This guarantees that when polling the messages on the receiver side, the timestamps always increase monotonically. We use this together with the observation that links between components in real systems always have some latency to provide synchronization slack. Essentially, if one side of the connection polls a message with time t, it can safely advance to timestamp t + link latency. The link latency is configured by the user.
    The link latency also helps with the frequency of synchronization messages. If we already sent a synchronization message containing t, then it suffices to only send another one when our local clock reaches t + link latency since the connected simulator, due to the link latency, couldn’t process any message from us in the meantime anyway. For accurate simulation, it therefore suffices to periodically send synchronization messages with the link latency as the period.
    There is one last optimization. Every message carries a timestamp and can therefore serve as an implicit synchronization message. Whenever we send a message at time t, we can therefore reschedule sending a synchronization message to t + link latency. Depending on the expected frequency of messages, rescheduling may be more expensive than just sending the synchronization message periodically. This is, for example, the case for gem5.

.. synchronized vs. unsynchronized
    SimBricks offers two modes of operation, unsynchronized and synchronized, which are defined on a per component basis. The default is the unsynchronized mode that is meant purely for functional testing. Unsynchronized components advance virtual time as quickly as they possibly can, which means that measurements taken on them are meaningless and cross-component measurements inaccurate.
    The synchronized mode, in contrast, is meant for accurate measurements and has to be enabled per component, for example, by setting simbricks.orchestration.simulators.PCIDevSim.sync_mode or simbricks.orchestration.simulators.HostSim.sync_mode. Running synchronized means that a simulator waits to process incoming messages from connected simulators at the correct timestamps. For technical details, see Synchronization.

..
    Link Latency and Sync period
    Most of the pre-defined simulators in orchestration/simulators.py provide an attribute for tuning link latencies and the synchronization period. Both are configured in nanoseconds and apply to the message flow from the configured simulator to connected ones.
    Some simulators have interfaces for different link types, for example, NIC simulators based on NICSim have a PCIe interface to connect to a host and an Ethernet link to connect to the network. The link latencies can then be configured individually per interface type.
    The synchronization period defines the simulator’s time between sending synchronization messages to connected simulators. Generally, for accurate simulations, you want to configure this to the same value as the link latency. This ensures an accurate simulation. With a lower value we don’t lose accuracy, but we send more synchronization messages than necessary. The other direction is also possible to increase simulation performance by trading-off accuracy using a higher setting. For more information, refer to the section on Synchronization in the Architectural Overview.



.. _sec-simulator-integration-implementation:

Implementation
==============================

.. the two steps that must be done
    The first step is to implement a SimBricks adapter in the simulator you want to integrate. This adapter on one side uses the simulator’s extension API to act as a native device and on the other side sends and receives SimBricks messages. You can find more information on adapters in our Architectural Overview.
    To make running experiments and setting up the SimBricks communication channels to other simulators convenient, add a class for the simulator in orchestration/simulators.py` that inherits either from Simulator or one of the more specialized base classes in. In this class, you define the command(s) to execute the simulator together with further parameters, for example, to connect to the communication channels with other simulators. Below is an example of what this looks like.

Protocol
------------------------------

..
    Let’s walk through the memory protocol as a simple example. 
    It is defined in the file lib/simbricks/mem/proto.h and is used for the simulation of memory disaggregated systems.
    The high-level idea of memory disaggregation is that the host’s memory resides somewhere externally, for example, it could be attached via the network.
    To simulate such a system, we introduced a simple memory simulator.
    In terms of the interface, the host issues read or write requests to the memory.
    For reads, the memory replies with the read value as the message’s payload.
    Writes can be either regular or posted. For the former, the memory replies with a completion message while posted writes are send-and-forget.
    Notice that this interface is asymmetric, which means that we have to take into account the two directions when defining the different message types: host to memory (h2m) and memory to host (m2h).
    An interface doesn’t have to necessarily be asymmetric. SimBricks also comes with a protocol for Ethernet (lib/simbricks/network/proto.h).
    Here, both sides transmit Ethernet packets to the other side in a send-and-forget manner, which is symmetric.
    To define the layout of the different message types for the memory or any other interface-specific protocol, we simply add a struct per type containing the fields.
    When an Adapter receives a message, it selects the correct struct using the own_type field from the base protocol.
    For this, a unique integer to store in the own_type field is required per type.
    It mustn’t collide with those used in the base SimBricks protocol, collisions with other interface-specific protocols, however, are fine.
    Similarly, we must ensure to not overwrite the base protocol’s fields with something else.


Adapter
------------------------------

To integrate a new simulator with SimBricks for the first time, a user needs to implement an adapter between the SimBricks interface and the simulators
internal abstractions.

SimBricks interfaces are based on the natural components boundaries, with simulators connected through message passing via these interfaces.


Orchestration Framework
------------------------------

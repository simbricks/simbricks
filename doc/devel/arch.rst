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
.. _page-architectural-overview:

###################################
Architectural Overview
###################################

On this page, we provide an overview of SimBrick's architecture and how it
connects existing simulators into an end-to-end virtual testbed. In the end, you
should have all the required knowledge to extend SimBricks by adding a new
Simulator or interface. Feel free to reach out to us if you have any questions
or want to discuss an idea. :ref:`sec-troubleshoot-getting-help` provides
information on how to do so.


Connecting Simulators
---------------------

We begin by introducing the high-level idea for connecting existing simulators.
For the moment, assume we are working with a simple system made up of just two
simulators, for example, a host simulator like gem5 that we want to connect to
some simulator for a PCIe device.

In a real system, components connect through common interfaces like PCIe or
Ethernet. Many simulators already expose an API for extending the simulation
with components or devices that attach through these interfaces. SimBricks uses
so-called adapters to emulate these, leveraging the provided API and forwarding
events of interest to the adapter in the other connected simulator using the
SimBricks protocol. This approach ensures modularity, or the ability to flexibly
combine simulators into a virtual testbed. Adding adapters at common interfaces
means that you can swap out one simulator for another without having to change
the adapter at the other side of the connection under the assumption that the
interface doesn't change. For example, adding a PCIe adapter to our host
simulator allows us to connect any simulator that implements a device-side PCIe
adapter to it. This approach even works for closed-source simulators as long as
they offer the necessary extensibility.

In the previous paragraph, we deliberately differentiated between host-side and
device-side PCIe adapters. The reason is that, depending on the concrete
interface, the two sides of a connection are not necessarily symmetric. In the
case of PCIe, the host can initiate BAR and PCIe config reads or writes. The
device, on the other hand, performs DMA and raises interrupts. This is an
important consideration when implementing the adapter and defining the protocol
used for the communication between them.

.. _fig-experiment-architecture:
.. figure:: https://raw.githubusercontent.com/simbricks/simbricks.github.io/4a474cfaf16f289fdf2c25601bbe1d9e02838f48/images/simbricks_example.svg
  :alt: example of a modular SimBricks simulation experiment
  
  A modular SimBricks simulation experiment. We can connect different simulators
  into an end-to-end virtual testbed by adding SimBricks adapters at natural
  boundaries like PCIe and Ethernet. Adapters always communicate in pairs
  exchanging messages which contain events of interest. The SimBricks protocol 
  is used for communication, which also offers special messages to synchronize
  the respective simulators if necessary.


SimBricks Protocol
------------------

So far, we only talked about connecting two simulators and omitted the details
of the protocol the respective adapters are using to exchange events of
interest. Even in more complex systems, simulators and therefore also their
adapters, are always connected pair-wise. A single simulator can have multiple
adapters though, which are connected to adapters in multiple other simulators.
You can see this in action in :numref:`fig-experiment-architecture`.

Two adapters communicate over a pair of optimized shared memory queues, sending
and polling SimBricks protocol messages containing information about events in a
FIFO manner. From each adapter's point of view, there is one send and receive
queue, respectively. Each adapter polls for messages in its receive queue, which
ensures the fastest simulation time as long as every simulator runs on its own
physical CPU core.

For the messages itself, interface-specific protocols are defined on top of the
base SimBricks protocol (:lib-simbricks:`base/proto.h#L118-L131`). The base
SimBricks protocol stores two important fields at fixed offsets within the
header (first 64 bytes) of each message:

* ``own_type`` - An integer identifying the type of message, required to
  correctly interpret the message when processing it later.
* ``timestamp`` - Timestamp when the event occurred. Required when synchronizing
  to process the event at the correct time in the receiving simulator.

Aside from these fields, the header layout can be freely customized by the
interface-specific protocol. Additionally, the message size is freely
configurable per interface to accommodate payloads of arbitrary size.

Let's walk through the memory protocol as a simple example. It is defined in the
file :lib-simbricks:`mem/proto.h` and is used for the simulation of memory
disaggregated systems. The high-level idea of memory disaggregation is that the
host's memory resides somewhere externally, for example, it could be attached
via the network. To simulate such a system, we introduced a simple memory
simulator. In terms of the interface, the host issues read or write requests to
the memory. For reads, the memory replies with the read value as the message's
payload. Writes can be either regular or posted. For the former, the memory
replies with a completion message while posted writes are send-and-forget.

Notice that this interface is asymmetric, which means that we have to take into
account the two directions when defining the different message types: host to
memory (h2m) and memory to host (m2h). An interface doesn't have to necessarily
be asymmetric. SimBricks also comes with a protocol for Ethernet
(:lib-simbricks:`network/proto.h`). Here, both sides transmit Ethernet packets
to the other side in a send-and-forget manner, which is symmetric.

To define the layout of the different message types for the memory or any other
interface-specific protocol, we simply add a struct per type containing the
fields. When an adapter receives a message, it selects the correct struct using
the ``own_type`` field from the base protocol. For this, a unique integer to
store in the ``own_type`` field is required per type. It mustn't collide with
those used in the base SimBricks protocol, collisions with other
interface-specific protocols, however, are fine. Similarly, we must ensure to
not overwrite the base protocol's fields with something else.


.. _sec-synchronization:

Synchronization
---------------

So far, we only covered transmitting important events in one simulator to
another. In case you are just interested in functional simulation, for example,
for debugging or functional testing, you can run the whole virtual testbed
unsynchronized for the lowest simulation time and skip this section. In order to
get sensible end-to-end measurements, however, you need to synchronize the
advancement of virtual time between the simulators.

Synchronization in the case of SimBricks means informing the connected simulator
that there will be no more messages to process up to some concrete timestamp.
For this, the base protocol defines a special synchronization message type.
Synchronization messages are sent over the same pair of send and receive queues
as the interface-specific messages. However, sending these for every tick of a
simulator's virtual clock doesn't scale. We can use some of SimBricks'
properties to reduce their number. First, we don't need to synchronize
simulators globally. Instead, it suffices to only do so pair-wise along the
connections between adapters. In particular, this means that we don't have to
synchronize simulators that aren't directly connected.

Furthermore, all messages are inserted into the shared memory queues in FIFO
order of when their respective event occurred in the sending simulator. This
guarantees that when polling the messages on the receiver side, the timestamps
always increase monotonically. We use this together with the observation that
links between components in real systems always have some latency to provide
synchronization slack. Essentially, if one side of the connection polls a
message with time ``t``, it can safely advance to timestamp ``t + link
latency``. The link latency is configured by the user.

The link latency also helps with the frequency of synchronization messages. If
we already sent a synchronization message containing ``t``, then it suffices to
only send another one when our local clock reaches ``t + link latency`` since
the connected simulator, due to the link latency, couldn't process any message
from us in the meantime anyway. For accurate simulation, it therefore suffices
to periodically send synchronization messages with the link latency as the
period.

There is one last optimization. Every message carries a timestamp and can
therefore serve as an implicit synchronization message. Whenever we send a
message at time ``t``, we can therefore reschedule sending a synchronization
message to ``t + link latency``. Depending on the expected frequency of
messages, rescheduling may be more expensive than just sending the
synchronization message periodically. This is, for example, the case for gem5.

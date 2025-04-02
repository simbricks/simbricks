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

.. _sec-orchestration-framework:

Orchestration Framework for Virtual Prototypes
**********************************************


System Configuration 
==============================

..
  NOTE: WHEN SPEAKING OF CHANNELS, MENTION THIS AND REFERENCE THE SYNCHRONIZATION SECTION!!!!!!!!!!!
    Link Latency and Sync period
        Most of the pre-defined simulators in orchestration/simulators.py provide an attribute for tuning link latencies and the synchronization period.
        Both are configured in nanoseconds and apply to the message flow from the configured simulator to connected ones.
        Some simulators have interfaces for different link types, for example, NIC simulators based on NICSim have a PCIe interface to connect to a host and an Ethernet link to connect to the network.
        The link latencies can then be configured individually per interface type.
        The synchronization period defines the simulator’s time between sending synchronization messages to connected simulators.
        Generally, for accurate simulations, you want to configure this to the same value as the link latency.
        This ensures an accurate simulation.
        With a lower value we don’t lose accuracy, but we send more synchronization messages than necessary.
        The other direction is also possible to increase simulation performance by trading-off accuracy using a higher setting.
        For more information, refer to the section on Synchronization in the Architectural Overview.


Simulation Configuration
==============================


Instantiation Configuration
==============================

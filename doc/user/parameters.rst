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

###################################
TAS Command-Line Parameters
###################################

******************************
IP Configuration
******************************

   *  ``--ip-addr=ADDR[/PREFIXLEN]``

      Set local IP address. Currently only exactly one IP address is supported.

   *  ``--ip-route=DEST[/PREFIX],NEXTHOP``

      Add an IP route for the destination subnet ``DEST/PREFIX`` via ``NEXTHOP``.
      Can be specified more than once.
      For example, a default route could be ``--ip-route=0.0.0.0/0,192.168.1.1``.


******************************
Fast Path Configuration
******************************

   *  ``--fp-cores-max=CORES``

      Maximum number of cores to use for fast-path. (default: 1)

   *  ``--fp-no-ints``

      Disable receive interrupts in the NIC driver, switches over to just
      polling.

   *  ``--fp-no-xsumoffload``

      Disable transmit checksum offloads, primarily useful to run TAS with NICs
      that do not support checksum offload, but comes at a slight performance
      cost.

   *  ``--fp-no-autoscale``

      Disable auto scaling, instead fix the number of cores used by the fast
      path to the maximum.

   *  ``--fp-no-hugepages``

      Do not use huge pages for the shared memory region between TAS and
      applications. (DPDK still uses huge pages for it's buffers unless
      explicitly disabled through ``--dpdk-extra``)

   *  ``--dpdk-extra=ARG``

      Pass ``ARG`` through as a parameter to the dpdk EAL. (see
      https://doc.dpdk.org/guides/linux_gsg/linux_eal_parameters.html)


******************************
TCP Protocol Parameters
******************************

   *  ``--tcp-rtt-init=RTT``

      Initial RTT used for congestion control. Is updated with actual
      measurements when they arrive.

   *  ``--tcp-link-bw=BANDWIDH``

      Link bandwidth in GBPS. TODO: what is this used for? (default: 10).

   *  ``--tcp-rxbuf-len=LEN``

      Connection receive buffer len in bytes (default: 8,192).

   *  ``--tcp-txbuf-len=LEN``

      Connection transmit buffer len in bytes (default: 8,192).

   *  ``--tcp-handshake-timeout=TIMEOUT``

      TCP handshake timeout in microseconds (default 10,000us).

   *  ``--tcp-handshake-retries=RETRIES``

      Maximum retries for timeouts during handshake.  (default: 10).


******************************
Congestion Control Parameters
******************************

   *  ``--cc=ALGORITHM``

      Choose which congestion control algorithm to use. The supported options
      are:

         +  ``dctcp-rate``: dctcp algorithm adapted to directly operate on the
            connection rate.

         +  ``dctcp-win``: original dctcp algorithm with the window converted to
            a rate for enforcement.

         + ``timely``: latency-based TIMELY control law.

         + ``const-rate``: set all connections to a constant rate (effectively
           disables congestion control, useful for debugging).

   *  ``--cc-control-interval=INT``

      Control interval length as multiples of the connection's RTT. (default: 2)

   *  ``--cc-control-granularity=G``

      Minimal control loop granularity. Control loop is only executed at most
      once every ``G`` microseconds. (default: 50)

   *  ``--cc-rexmit-ints=INTERVALS``

      Number of connection cnotrol intervals before TAS triggers a re-transmit.
      (default: 4).

DCTCP
=========================
For the ``dctcp-rate`` and ``dctcp-win`` algorithm:

   *  ``--cc-dctcp-weight=WEIGHT``

      EWMA weight for dctcp's ECN rate (alpha, default: 0.0625).

   *  ``--cc-dctcp-mimd=INC_FACT``

      Enable mutliplicative increase by ``INC_FACT`` (disabled by default, only
      used for tests).

   *  ``--cc-dctcp-min=RATE``

      Minimum rate to set for flows (kbps, default: 10000).

Timely
=========================
Parameters for the ``timely`` algorithm:

   *  ``--cc-timely-tlow=TIME``

      Tlow threshold in microseconds. (default: 30)

   *  ``--cc-timely-thigh=TIME``

      Thigh threshold in microseconds. (default: 150)

   *  ``--cc-timely-step=STEP``

      Additive increase step size in kbps (default: 10000)

   *  ``--cc-timely-init=RATE``

      Initial connection rate in kbps (default: 10000)

   *  ``--cc-timely-alpha=FRAC``

      EWMA weight for rtt diff. (default: 0.02)

   *  ``--cc-timely-beta=FRAC``

      Multiplicative decrease factor. (default: 0.8)

   *  ``--cc-timely-minrtt=RTT``

      Minimal RTT without queueing in microseconds. (default: 11)

   *  ``--cc-timely-minrate=RTT``

      Minimal connection rate to use in kbps (default: 10000)

Constant Rate
=========================
For the ``const-rate`` "algorithm" the following configuration options apply:

   *  ``--cc-const-rate=RATE``

      Sets the rate to use in kbps.


******************************
ARP Protocol Parameters
******************************

   *  ``--arp-timeout=TIMEOUT``

      Initial ARP request timetout in microseconds. This doubles with every
      retry (default: 500).

   *  ``--arp-timeout-max=TIMEOUT``

      Maximal ARP timeout in microseconds. If the retry-timeout grows larger
      than this, the request fails. (default: 10,000,000 us)


******************************
Slowpath Queues
******************************

   *  ``--nic-rx-len=LEN``

      Number of entries in TAS slowpath receive queue. (default: 16,384).

   *  ``--nic-tx-len=LEN``

      Number of entries in TAS slowpath transmit queue. (default: 16,384).

   *  ``--app-kin-len=LEN``

      Application slow path receive queue length in bytes. (default: 1,048,576).

   *  ``--app-kout-len=LEN``

      Application slow path transmit queue length in bytes. (default: 1,048,576).


******************************
Host Kernel Interface
******************************

   *  ``--kni-name=NAME``

      Enables the DPDK kernel network interface, by creating a dummy network
      interface with the name ``NAME``. (default: disabled)


******************************
Miscellaneous
******************************

   *  ``--quiet``

       Disable non-essential logging.

   *  ``--ready-fd=FD``

      Causes TAS to write to file descriptor ``FD`` when ready. Can be used by
      supervisor processes to detect when TAS is ready, e.g. used in full system
      tests.

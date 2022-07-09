# Copyright 2021 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

########################################################################
# This script is for generating the result in 8.1 in the paper.
#
# In each simulation, two hosts are connected by a switch
# [HOST_0] - [NIC_0] ---- [SWITCH] ----  [NIC_1] - [HOST_1]
#  server                                           client
#
# The server host runs netperf server and client host runs TCP_RR and
# TCP_STREAM test
#
# The command to run all the experiments is:
# $: python3 run.py pyexps/ae/corundum_pcilat.py --filter cblat-gt-sw --verbose --force
########################################################################

import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

import simbricks.experiments as exp

pci_latency = [1000]
experiments = []

for pci_type in pci_latency:

    e = exp.Experiment('cblat-gt-sw-' + f'{pci_type}')

    net = sim.SwitchNet()
    net.sync_period = pci_type
    net.eth_latency = pci_type
    e.add_network(net)

    host_class = sim.Gem5Host
    e.checkpoint = True

    def nic_pci():
        n = sim.CorundumBMNIC()
        n.sync_period = pci_type
        n.pci_latency = pci_type
        return n

    nic_class = nic_pci
    nc_class = node.CorundumLinuxNode

    # create servers and clients
    servers = create_basic_hosts(
        e,
        1,
        'server',
        net,
        nic_class,
        host_class,
        nc_class,
        node.NetperfServer
    )

    clients = create_basic_hosts(
        e,
        1,
        'client',
        net,
        nic_class,
        host_class,
        nc_class,
        node.NetperfClient,
        ip_start=2
    )

    for s in servers:
        s.pci_latency = pci_type
        s.sync_period = pci_type

    for c in clients:
        c.pci_latency = pci_type
        c.sync_period = pci_type
        c.wait = True
        c.node_config.app.server_ip = servers[0].node_config.ip

    # add to experiments
    experiments.append(e)

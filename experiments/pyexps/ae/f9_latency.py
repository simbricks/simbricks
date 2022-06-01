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
# This script is for reproducing [Figure 9] in the paper.
# It generates experiments for 
#
# Host type has qemu-kvm(qemu in short), gem5-timing-mode(gt), qemu-timing-mode(qt)
# Nic type has Intel_i40e behavioral model(ib), corundum behavioral model(cb), corundum verilator(cv)
# Net type has Switch behavioral model(sw), ns-3(ns3)
#
# In each simulation, two hosts are connected by a switch 
# [HOST_0] - [NIC_0] ---- [SWITCH] ----  [NIC_1] - [HOST_1]
#  server                                           client
# 
# The server host runs netperf server and client host runs TCP_RR and
# TCP_STREAM test
# 
# The command to run all the experiments is:
# $: python3 run.py pyexps/ae/t1_combination.py --filter nf-* --verbose
########################################################################


import simbricks.experiments as exp
import simbricks.simulators as sim
import simbricks.nodeconfig as node
from simbricks.simulator_utils import create_basic_hosts

pci_latency = [10, 50, 100, 500, 1000]
experiments = []

for pci_type in pci_latency:

    e = exp.Experiment('pci-gt-ib-sw-' + f'{pci_type}')

    net = sim.SwitchNet()
    e.add_network(net)

    host_class = sim.Gem5Host
    e.checkpoint = True

    nic_class = sim.I40eNIC
    nc_class = node.I40eLinuxNode

    # create servers and clients
    servers = create_basic_hosts(e, 1, 'server', net, nic_class, host_class,
            nc_class, node.NetperfServer)

    clients = create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
            nc_class, node.NetperfClient, ip_start = 2)

    for c in clients:
        c.wait = True
        c.node_config.app.server_ip = servers[0].node_config.ip

    # add to experiments
    experiments.append(e)

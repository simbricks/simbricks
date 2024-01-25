# Copyright 2022 Max Planck Institute for Software Systems, and
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
"""
Simple example experiment, which sets up a client and a server host connected
through a switch.

The client pings the server.
"""

from simbricks.orchestration.experiments import Experiment
from simbricks.orchestration.nodeconfig import (
    HomaClientNode, HomaServerNode, I40eLinuxNode, IdleHost, PingClient, NodeConfig
)
from simbricks.orchestration.simulators import QemuHost, Gem5Host, I40eNIC, SwitchNet

experiments = []
workload = [1,2,3,4,5]
host_types = ['qemu', 'gem5', 'qt']
for  w in workload:
    for host_type in host_types:

        e = Experiment(f'single_homa_w{w}_' + host_type)
        e.checkpoint = False  # use checkpoint and restore to speed up simulation
        # host
        if host_type == 'qemu':
            HostClass = QemuHost
        elif host_type == 'qt':

            def qemu_timing(node_config: NodeConfig):
                h = QemuHost(node_config)
                h.sync = True
                return h

            HostClass = qemu_timing
        elif host_type == 'gem5':
            HostClass = Gem5Host
            e.checkpoint = True
        else:
            raise NameError(host_type)

        # create client
        client_config = I40eLinuxNode()  # boot Linux with i40e NIC driver
        client_config.disk_image = 'homa'
        client_config.ip = '10.0.0.1'
        client_config.app = HomaClientNode()
        client = HostClass(client_config)
        # client.sync = False
        client.name = 'client'
        client.wait = True  # wait for client simulator to finish execution
        e.add_host(client)

        # attach client's NIC
        client_nic = I40eNIC()
        e.add_nic(client_nic)
        client.add_nic(client_nic)

        # create server
        server_config = I40eLinuxNode()  # boot Linux with i40e NIC driver
        server_config.disk_image = 'homa'
        server_config.ip = '10.0.0.2'
        server_config.app = HomaServerNode()
        server = HostClass(server_config)
        # server.sync = False
        server.name = 'server'
        # server.wait = True
        e.add_host(server)

        # attach server's NIC
        server_nic = I40eNIC()
        e.add_nic(server_nic)
        server.add_nic(server_nic)

        # connect NICs over network
        network = SwitchNet()
        e.add_network(network)
        client_nic.set_network(network)
        server_nic.set_network(network)

        # set more interesting link latencies than default
        eth_latency = 500  # 500 us
        network.eth_latency = eth_latency
        client_nic.eth_latency = eth_latency
        server_nic.eth_latency = eth_latency

        experiments.append(e)

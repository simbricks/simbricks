# Copyright 2023 Max Planck Institute for Software Systems, and
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

import random
import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_components as e2e
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts
from simbricks.orchestration.e2e_topologies import (
    DCFatTree, add_homa_bg
)

random.seed(42)

types_of_host = ['qemu', 'qt', 'gem5']
types_of_protocol = ['tcp', 'homa']

options = {
    'ns3::TcpSocket::SegmentSize': '1448',
    'ns3::TcpSocket::SndBufSize': '524288',
    'ns3::TcpSocket::RcvBufSize': '524288',
    'ns3::Ipv4GlobalRouting::RandomEcmpRouting': '1',
}


experiments = []

for h in types_of_host:
    for p in types_of_protocol:
        e = exp.Experiment('e2e_homa_' + h + '_bg_' + p)

        def qemu_timing(node_config: node.NodeConfig):
            h = sim.QemuHost(node_config)
            h.sync = True
            return h
        
        if h == 'qemu':
            HostClass = sim.QemuHost
        elif h == 'qt':
            HostClass = qemu_timing
        elif h == 'gem5':
            HostClass = sim.Gem5Host
            e.checkpoint = False
        else:
            raise NameError(h)

        topology = DCFatTree(
                    n_spine_sw=1,
                    n_agg_bl=2,
                    n_agg_sw=1,
                    n_agg_racks=4,
                    h_per_rack=10,
                )
        

        net = sim.NS3E2ENet()
        net.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])
        net.e2e_global.stop_time = "60s"
        net.add_component(topology)
        if h == 'qemu':
            net.sync = False
        else:
            net.sync = True
        # net.wait = True
        e.add_network(net)
        
        # create client
        client_config = node.I40eLinuxNode()  # boot Linux with i40e NIC driver
        client_config.disk_image = 'homa'
        client_config.ip = '10.0.0.1'
        client_config.app = node.HomaClientNode()
        client_config.app.protocol = 'homa'
        client = HostClass(client_config)
        # client.sync = False
        client.name = 'client'
        client.wait = True  # wait for client simulator to finish execution
        e.add_host(client)

        # attach client's NIC
        client_nic = sim.I40eNIC()
        e.add_nic(client_nic)
        client.add_nic(client_nic)

        # create server
        server_config = node.I40eLinuxNode()  # boot Linux with i40e NIC driver
        server_config.disk_image = 'homa'
        server_config.ip = '10.0.0.2'
        server_config.app = node.HomaServerNode()
        server_config.app.protocol = 'homa'
        server = HostClass(server_config)
        # server.sync = False
        server.name = 'server'
        # server.wait = True
        e.add_host(server)

        # attach server's NIC
        server_nic = sim.I40eNIC()
        e.add_nic(server_nic)
        server.add_nic(server_nic)

        client_nic.set_network(net)
        server_nic.set_network(net)

        topology.add_simbricks_host_r(client_nic)
        topology.add_simbricks_host_r(server_nic)

        add_homa_bg(topology, app_proto=p, exp_name=e.name)
        net.init_network()

        experiments.append(e)

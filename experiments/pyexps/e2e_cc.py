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

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_components as e2e
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts
from simbricks.orchestration.e2e_topologies import E2EDumbbellTopology

# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu/gem5-timing
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: DCTCPm

#types_of_host = ['qemu', 'qt', 'gt', 'gO3']
types_of_host = ['gt']
#types_of_nic = ['cv', 'cb', 'ib']
types_of_nic = ['ib']
#types_of_net = ['dumbbell']
#types_of_app = ['DCTCPm']
types_of_mtu = [1500]
types_of_congestion_control = [e2e.CongestionControl.CUBIC]

num_ns3_hosts = 1
num_simbricks_hosts = 1
#max_k = 199680
#k_step = 16640
#k_step = 33280
link_rate = 200 # in Mbps
link_latency = 5 # in ms
bdp = int(link_rate * link_latency / 1000 * 10**6) # Bandwidth-delay product
cpu_freq = '5GHz'
cpu_freq_qemu = '2GHz'
sys_clock = '1GHz'  # if not set, default 1GHz

ip_start = '192.168.64.1'

experiments = []

# set network sim
NetClass = sim.NS3E2ENet

for congestion_control in types_of_congestion_control:
    for mtu in types_of_mtu:
        for k_val in range(0, 1):

            queue_size = int(bdp * 2**k_val)

            options = {
                'ns3::TcpSocket::SegmentSize': f'{mtu-52}',
                'ns3::TcpSocket::SndBufSize': '524288',
                'ns3::TcpSocket::RcvBufSize': '524288',
            }

            net = NetClass()
            net.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])

            topology = E2EDumbbellTopology()
            topology.data_rate = f'{link_rate}Mbps'
            topology.delay = f'{link_latency}ms'
            topology.queue_size = f'{queue_size}B'
            topology.mtu = f'{mtu-52}'
            net.add_component(topology)

            for i in range(1, num_ns3_hosts + 1):
                host = e2e.E2ESimpleNs3Host(f'ns3server-{i}')
                host.delay = '1us'
                host.data_rate = f'{link_rate}Mbps'
                host.ip = f'192.168.64.{i}/24'
                host.queue_size = f'{queue_size}B'
                host.congestion_control = congestion_control
                app = e2e.E2EPacketSinkApplication('sink')
                app.local_ip = '0.0.0.0:5000'
                app.stop_time = '20s'
                host.add_component(app)
                probe = e2e.E2EPeriodicSampleProbe('probe', 'Rx')
                probe.interval = '100ms'
                probe.file = f'sink-rx-{i}'
                app.add_component(probe)
                topology.add_left_component(host)

            for i in range(1, num_ns3_hosts + 1):
                host = e2e.E2ESimpleNs3Host(f'ns3client-{i}')
                host.delay = '1us'
                host.data_rate = f'{link_rate}Mbps'
                host.ip = f'192.168.64.{i+num_ns3_hosts+num_simbricks_hosts}/24'
                host.queue_size = f'{queue_size}B'
                host.congestion_control = congestion_control
                app = e2e.E2EBulkSendApplication('sender')
                app.remote_ip = f'192.168.64.{i}:5000'
                app.stop_time = '20s'
                host.add_component(app)
                topology.add_right_component(host)

            e = exp.Experiment(
                'gt-ib-dumbbell-' + str(congestion_control) + 'TCPm' +
                f'{k_val}' + f'-{mtu}'
            )
            e.add_network(net)

            freq = cpu_freq

            # simbricks host
            def gem5_timing(node_config: node.NodeConfig):
                h = sim.Gem5Host(node_config)
                #h.sys_clock = sys_clock
                return h

            HostClass = gem5_timing
            e.checkpoint = True

            NicClass = sim.I40eNIC
            NcClass = node.I40eTCPCongNode

            servers = create_tcp_cong_hosts(
                e,
                num_simbricks_hosts,
                'server',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.TcpCongServer,
                freq,
                mtu,
                congestion_control.gem5,
                ip_start=num_ns3_hosts + 1
            )
            clients = create_tcp_cong_hosts(
                e,
                num_simbricks_hosts,
                'client',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.TcpCongClient,
                freq,
                mtu,
                congestion_control.gem5,
                ip_start=2*num_ns3_hosts + num_simbricks_hosts + 1
            )

            for i, server in enumerate(servers, 1):
                host = e2e.E2ESimbricksHost(f'simbricksserver-{i}')
                host.eth_latency = '1us'
                host.simbricks_host = server.nics[0]
                topology.add_left_component(host)

            for i, client in enumerate(clients, 1):
                host = e2e.E2ESimbricksHost(f'simbricksclient-{i}')
                host.eth_latency = '1us'
                host.simbricks_host = client.nics[0]
                topology.add_right_component(host)

            i = 0
            for cl in clients:
                cl.node_config.app.server_ip = servers[i].node_config.ip
                i += 1

            # All the clients will not poweroff after finishing iperf test
            # except the last one This is to prevent the simulation gets
            # stuck when one of host exits.

            # The last client waits for the output printed in other hosts,
            # then cleanup
            clients[num_simbricks_hosts - 1].node_config.app.is_last = True
            clients[num_simbricks_hosts - 1].wait = True

            net.init_network()

            print(e.name)
            experiments.append(e)

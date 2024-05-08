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

import simbricks.orchestration.e2e_components as e2e
import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts

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
link_rate = 1000  # in Mbps
link_latency = 500  # in ns
bdp = int(link_rate * link_latency / 10**9 * 10**6)  # Bandwidth-delay product
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

            left_net = NetClass()
            left_net.name = 'left_net'
            left_net.opt = ' '.join([
                f'--{o[0]}={o[1]}' for o in options.items()
            ])
            right_net = NetClass()
            right_net.name = 'right_net'
            right_net.opt = ' '.join([
                f'--{o[0]}={o[1]}' for o in options.items()
            ])

            # left connects -> NetIf
            # right created socket -> NicIf

            left_switch = e2e.E2ESwitchNode('left_switch')
            left_switch.mtu = f'{mtu-52}'
            left_net.add_component(left_switch)
            right_switch = e2e.E2ESwitchNode('right_switch')
            right_switch.mtu = f'{mtu-52}'
            right_net.add_component(right_switch)

            left_adapter = e2e.E2ENetworkSimbricks('left_adapter')
            left_adapter.eth_latency = f'{link_latency}ns'
            left_adapter.simbricks_component = right_net
            left_adapter.listen = False
            left_switch.add_component(left_adapter)
            right_adapter = e2e.E2ENetworkSimbricks('right_adapter')
            right_adapter.eth_latency = f'{link_latency}ns'
            right_adapter.simbricks_component = left_net
            right_adapter.listen = True
            right_switch.add_component(right_adapter)

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
                left_switch.add_component(host)

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
                right_switch.add_component(host)

            e = exp.Experiment(
                'gt-ib-dumbbell-' + str(congestion_control) + 'TCPm' +
                f'{k_val}' + f'-{mtu}'
            )
            e.add_network(left_net)
            e.add_network(right_net)

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
                left_net,
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
                right_net,
                NicClass,
                HostClass,
                NcClass,
                node.TcpCongClient,
                freq,
                mtu,
                congestion_control.gem5,
                ip_start=2 * num_ns3_hosts + num_simbricks_hosts + 1
            )

            for i, server in enumerate(servers, 1):
                host = e2e.E2ESimbricksHost(f'simbricksserver-{i}')
                host.eth_latency = '1us'
                host.simbricks_component = server.nics[0]
                left_switch.add_component(host)

            for i, client in enumerate(clients, 1):
                host = e2e.E2ESimbricksHost(f'simbricksclient-{i}')
                host.eth_latency = '1us'
                host.simbricks_component = client.nics[0]
                right_switch.add_component(host)

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

            left_net.init_network()
            right_net.init_network()

            print(e.name)
            experiments.append(e)

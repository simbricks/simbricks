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

import typing as tp

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_components as e2e
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts
from simbricks.orchestration.e2e_helpers import E2ELinkAssigner, E2ELinkType

mtu = 1500
congestion_control = e2e.CongestionControl.CUBIC

num_ns3_hosts = 1
num_simbricks_hosts = 1

link_rate = 1000  # in Mbps
link_latency = 500  # in ns
bdp = int(link_rate * link_latency / 10**9 * 10**6)  # Bandwidth-delay product
queue_size = bdp
cpu_freq = '5GHz'
cpu_freq_qemu = '2GHz'
sys_clock = '1GHz'  # if not set, default 1GHz

ip_start = '192.168.64.1'

experiments = []

# set network sim
NetClass = sim.NS3E2ENet

for link_type in (E2ELinkType.NS3_SIMPLE_CHANNEL, E2ELinkType.SIMBRICKS):

    options = {
        'ns3::TcpSocket::SegmentSize': f'{mtu-52}',
        'ns3::TcpSocket::SndBufSize': '524288',
        'ns3::TcpSocket::RcvBufSize': '524288',
    }

    # Create three switches
    left_switch_0 = e2e.E2ESwitchNode('left_switch_0')
    left_switch_0.mtu = f'{mtu-52}'
    left_switch_1 = e2e.E2ESwitchNode('left_switch_1')
    left_switch_1.mtu = f'{mtu-52}'
    right_switch_0 = e2e.E2ESwitchNode('right_switch_0')
    right_switch_0.mtu = f'{mtu-52}'

    assigner = E2ELinkAssigner()

    # Connect left_switch_1 to left_switch_0 with ns3 link
    assigner.add_link(
        f'{left_switch_1.id}_{left_switch_0.id}',
        left_switch_1,
        left_switch_0,
        E2ELinkType.NS3_SIMPLE_CHANNEL
    )

    # Connect left_switch_0 to right_switch_0 with either ns3 or simbricks link
    assigner.add_link(
        f'{left_switch_0.id}_{right_switch_0.id}',
        left_switch_0,
        right_switch_0,
        link_type
    )

    # Create the links and ns3 instances
    networks = assigner.assign_networks()

    current_ip = 1

    def add_ns3_client_server(client_switch, server_switch, ip):
        host = e2e.E2ESimpleNs3Host(f'ns3client-{ip}')
        host.delay = '1us'
        host.data_rate = f'{link_rate}Mbps'
        host.ip = f'192.168.64.{ip}/24'
        host.queue_size = f'{queue_size}B'
        host.congestion_control = congestion_control
        app = e2e.E2EBulkSendApplication('sender')
        app.remote_ip = f'192.168.64.{ip+1}:5000'
        app.stop_time = '20s'
        host.add_component(app)
        client_switch.add_component(host)

        host = e2e.E2ESimpleNs3Host(f'ns3server-{ip+1}')
        host.delay = '1us'
        host.data_rate = f'{link_rate}Mbps'
        host.ip = f'192.168.64.{ip+1}/24'
        host.queue_size = f'{queue_size}B'
        host.congestion_control = congestion_control
        app = e2e.E2EPacketSinkApplication('sink')
        app.local_ip = '0.0.0.0:5000'
        app.stop_time = '20s'
        host.add_component(app)
        probe = e2e.E2EPeriodicSampleProbe('probe', 'Rx')
        probe.interval = '100ms'
        probe.file = f'sink-rx-{ip+1}'
        app.add_component(probe)
        server_switch.add_component(host)

    # Add a few ns3 hosts
    add_ns3_client_server(left_switch_1, left_switch_0, current_ip)
    current_ip += 2
    add_ns3_client_server(left_switch_0, right_switch_0, current_ip)
    current_ip += 2
    add_ns3_client_server(left_switch_1, right_switch_0, current_ip)
    current_ip += 2

    e = exp.Experiment(
        'e2e-as-' + str(congestion_control) + f'-{link_type.name}' + f'-{mtu}'
    )

    for network in networks:
        network.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])
        e.add_network(network)
        # Set params of created links
        for component in network.e2e_components:
            if isinstance(component, e2e.E2ESimpleChannel):
                component.data_rate = f'{link_rate}Mbps'
                component.queue_size = f'{queue_size}B'
                component.delay = f'{link_latency}ns'
            elif isinstance(component, (e2e.E2ENetworkSimbricks)):
                component.eth_latency = f'{link_latency}ns'

    # simbricks host
    def gem5_timing(node_config: node.NodeConfig):
        h = sim.Gem5Host(node_config)
        #h.sys_clock = sys_clock
        return h

    HostClass = gem5_timing
    e.checkpoint = True

    NicClass = sim.I40eNIC
    NcClass = node.I40eTCPCongNode

    def add_gem5_client_server(
        client_switch, server_switch, host_class, nic_class, nc_class, ex, ip
    ):

        c = create_tcp_cong_hosts(
            ex,
            1,
            f'client-{ip}',
            tp.cast(sim.NS3E2ENet, client_switch.network),
            nic_class,
            host_class,
            nc_class,
            node.TcpCongClient,
            cpu_freq,
            mtu,
            congestion_control.gem5,
            ip_start=ip
        )[0]
        host = e2e.E2ESimbricksHost(f'simbricksclient-{ip}')
        host.eth_latency = '1us'
        host.simbricks_component = c.nics[0]
        client_switch.add_component(host)

        s = create_tcp_cong_hosts(
            ex,
            1,
            f'server-{ip+1}',
            tp.cast(sim.NS3E2ENet, server_switch.network),
            nic_class,
            host_class,
            nc_class,
            node.TcpCongServer,
            cpu_freq,
            mtu,
            congestion_control.gem5,
            ip_start=ip + 1
        )[0]
        host = e2e.E2ESimbricksHost(f'simbricksserver-{ip+1}')
        host.eth_latency = '1us'
        host.simbricks_component = s.nics[0]
        server_switch.add_component(host)

        c.node_config.app.server_ip = s.node_config.ip
        return c

    clients = []

    client = add_gem5_client_server(
        left_switch_1,
        right_switch_0,
        HostClass,
        NicClass,
        NcClass,
        e,
        current_ip
    )
    clients.append(client)
    current_ip += 2
    client = add_gem5_client_server(
        left_switch_0,
        right_switch_0,
        HostClass,
        NicClass,
        NcClass,
        e,
        current_ip
    )
    clients.append(client)
    current_ip += 2

    # All the clients will not poweroff after finishing iperf test
    # except the last one This is to prevent the simulation gets
    # stuck when one of host exits.

    # The last client waits for the output printed in other hosts,
    # then cleanup
    clients[num_simbricks_hosts - 1].node_config.app.is_last = True
    clients[num_simbricks_hosts - 1].wait = True

    for network in networks:
        network.init_network()

    print(e.name)
    experiments.append(e)

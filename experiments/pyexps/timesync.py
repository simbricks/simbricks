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

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_topologies as e2e
from simbricks.orchestration.simulator_utils import create_basic_hosts
import urllib.parse
import random


class TimesyncNode(node.I40eLinuxNode):

    def __init__(self):
        super().__init__()
        self.disk_image = 'timesync'
        self.memory = 8192

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'ip link set dev lo up',
            #'ip addr add 127.0.0.1/8 dev lo',
        ]


class ChronyServer(node.AppConfig):

    def __init__(self):
        super().__init__()
        self.loglevel = 0

    def config_files(self):
        cfg = (
            f'bindcmdaddress 127.0.0.1\n'
            f'allow 10.0.0.0/8\n'
            f'driftfile /tmp/chrony-drift\n'
            f'local stratum 1\n'
            )
        m = {'chrony.conf': self.strfile(cfg)}
        return m

    def run_cmds(self, node):
        return [f'chronyd -d -x -f chrony.conf -L {self.loglevel}']


class ChronyClient(node.AppConfig):

    def __init__(self):
        super().__init__()
        self.chrony_loglevel = 0
        self.ntp_server = '10.0.0.1'

    def config_files(self):
        cfg = (
            f'bindcmdaddress 127.0.0.1\n'
            f'server {self.ntp_server} iburst minpoll -6 maxpoll -1\n'
            f'driftfile /tmp/chrony-drift\n'
            f'makestep 0.01 3\n'
            )
        m = {'chrony.conf': self.strfile(cfg)}
        return m

    def run_cmds(self, node):
        return [f'sleep 0.5',
                f'chronyd -d -f chrony.conf -L {self.chrony_loglevel} &',
                f'sleep 1',
                f'(while true; do chronyc tracking; sleep 1; done) &']


class ChronyTestClient(ChronyClient):

    def __init__(self):
        super().__init__()

    def run_cmds(self, node):
        return super().run_cmds(node) + [
                f'sleep 5'
                ]

class CockroachServer(ChronyClient):

    def __init__(self):
        super().__init__()
        self.servers = []

    def prepare_pre_cp(self, node):
        return super().prepare_pre_cp(node) + [
            (f'cp /root/cockroach/server-certs/{node.ip}.crt '
                f'/root/cockroach/certs/node.crt'),
            (f'cp /root/cockroach/server-certs/{node.ip}.key '
                f'/root/cockroach/certs/node.key')
            ]


    def run_cmds(self, node):
        servers = ','.join([f'{ip}:26257' for ip in self.servers])
        return super().run_cmds(node) + [
                (f'/usr/local/bin/cockroach start '
                    f'--certs-dir=/root/cockroach/certs/ '
                    f'--store=/tmp/cockroach '
                    f'--listen-addr={node.ip}:26257 '
                    f'--http-addr={node.ip}:8080 '
                    f'--join={servers} '
                    f'--max-offset=10ms '),
                'wait'
                ]

class CockroachClient(ChronyClient):

    def __init__(self):
        super().__init__()
        self.init = False
        self.servers = []
        self.workload = 'social'
        self.workload_init_args = '--splits=3'
        self.workload_args = '--splits=3 --concurrency 100'

    def run_cmds(self, node):
        server_ports = [f'{ip}:26257' for ip in self.servers]
        i = int(node.ip.split('.')[-1]) % len(server_ports)
        sp = server_ports[i]

        cd = '/root/cockroach/certs/'.replace('/', '%2F')
        connstr = (
            f'postgresql://root@{sp}?sslcert={cd}client.root.crt&'
            f'sslkey={cd}client.root.key&sslmode=verify-full&'
            f'sslrootcert={cd}ca.crt')

        cmds = ['sleep 2']
        if self.init:
            cmds.append(
                f'/usr/local/bin/cockroach init '
                f'--certs-dir=/root/cockroach/certs/ '
                f'--host={sp}')
            cmds.append('sleep 1')
            cmds.append(
                f'/usr/local/bin/cockroach workload init {self.workload} '
                f'{self.workload_init_args} "{connstr}"')
            cmds.append('sleep 0.5')
        else:
            cmds.append('sleep 4')
        cmds.append(
            f'/usr/local/bin/cockroach workload run {self.workload} '
                f'--duration=10s {self.workload_args} "{connstr}"')
        http = f'https://{self.servers[i]}:8080/_status/vars'
        cmds.append(f'curl -k {http}')
        return super().run_cmds(node) + cmds

kinds_of_host = ['qemu','qemu_sync']
kinds_of_net = ['switch', 'dc', 'dcbg']

experiments = []

random.seed(42)

class DCNetSim(sim.NS3E2ENet):

    def __init__(self, topo_args={}) -> None:
        super().__init__()

        options = {
            'ns3::TcpSocket::SegmentSize': '1448',
            'ns3::TcpSocket::SndBufSize': '524288',
            'ns3::TcpSocket::RcvBufSize': '524288',
            'ns3::Ipv4GlobalRouting::RandomEcmpRouting': '1',
        }
        self.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])

        self.dc_topo = e2e.DCFatTree(
                    n_spine_sw=1,
                    n_agg_bl=4,
                    n_agg_sw=1,
                    n_agg_racks=4,
                    h_per_rack=10,
                )
        self.add_component(self.dc_topo)

    def connect_nic(self, nic):
        super().connect_nic(nic)
        self.dc_topo.add_simbricks_host_r(nic)

class DCBgNetSim(DCNetSim):

    def __init__(self, topo_args={}, bg_args={}) -> None:
        super().__init__(topo_args=topo_args)
        self.bg_args = bg_args

    def instantiate(self):
        e2e.add_contig_bg(self.dc_topo, **self.bg_args)
        super().instantiate()

for h in kinds_of_host:
    def qemu_timing(node_config: node.NodeConfig):
        h = sim.QemuHost(node_config)
        h.sync = True
        return h
    if h == 'qemu':
        HostClass = sim.QemuHost
    if h == 'qemu_sync':
        HostClass = qemu_timing
    # set network sim
    for n in kinds_of_net:
        if n == 'switch':
            NetClass = sim.SwitchNet
        elif n == 'dc':
            NetClass = DCNetSim
        elif n == 'dcbg':
            NetClass = DCBgNetSim
        net = NetClass()

        e = exp.Experiment('timesync-' + h +'-' + n)
        #net.pcap_file = 'out/' + e.name + '.pcap'
        if h == 'qemu':
            net.sync = False
        e.add_network(net)

        ntp_servers = create_basic_hosts(
            e,
            1,
            'ntpserv',
            net,
            sim.I40eNIC,
            HostClass,
            TimesyncNode,
            ChronyServer
        )
        servers = create_basic_hosts(
            e,
            2,
            'server',
            net,
            sim.I40eNIC,
            HostClass,
            TimesyncNode,
            CockroachServer,
            ip_start=2
        )
        clients = create_basic_hosts(
            e,
            4,
            'client',
            net,
            sim.I40eNIC,
            HostClass,
            TimesyncNode,
            CockroachClient,
            ip_start=32
        )

        server_ips = [s.node_config.ip for s in servers]

        for hh in servers + clients:
            hh.node_config.app.servers = server_ips
            hh.node_config.app.ntp_server = \
                    ntp_servers[0].node_config.ip

        clients[0].wait = True
        clients[0].node_config.app.init = True

        #for hh in servers + clients:
        #    hh.sync_drift = int(random.gauss(mu=1000.0, sigma=10))
        #    hh.sync_offset = int(random.uniform(0.0, 1000000.0))
        #    print(f'host {hh.name}: drift={hh.sync_drift} offset={hh.sync_offset}')

        experiments.append(e)

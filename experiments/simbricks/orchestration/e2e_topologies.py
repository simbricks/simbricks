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

# Allow own class to be used as type for a method's argument
from __future__ import annotations

from abc import ABC, abstractmethod
import ipaddress
import random

import simbricks.orchestration.e2e_components as e2e


class E2ETopology(ABC):

    @abstractmethod
    def add_to_network(self, net):
        pass

    @abstractmethod
    def get_switches(self):
        pass

    @abstractmethod
    def get_links(self):
        pass


class E2EDumbbellTopology(E2ETopology):

    def __init__(self):
        self.left_switch = e2e.E2ESwitchNode("_leftSwitch")
        self.right_switch = e2e.E2ESwitchNode("_rightSwitch")
        self.link = e2e.E2ESimpleChannel("_link")
        self.link.left_node = self.left_switch
        self.link.right_node = self.right_switch

    def add_to_network(self, net):
        net.add_component(self.left_switch)
        net.add_component(self.right_switch)
        net.add_component(self.link)

    def add_left_component(self, component: e2e.E2EComponent):
        self.left_switch.add_component(component)

    def add_right_component(self, component: e2e.E2EComponent):
        self.right_switch.add_component(component)

    @property
    def mtu(self):
        return self.left_switch.mtu

    @mtu.setter
    def mtu(self, mtu: str):
        self.left_switch.mtu = mtu
        self.right_switch.mtu = mtu

    @property
    def data_rate(self):
        return self.link.data_rate

    @data_rate.setter
    def data_rate(self, data_rate: str):
        self.link.data_rate = data_rate

    @property
    def queue_size(self):
        return self.link.queue_size

    @queue_size.setter
    def queue_size(self, queue_size: str):
        self.link.queue_size = queue_size

    @property
    def delay(self):
        return self.link.delay

    @delay.setter
    def delay(self, delay: str):
        self.link.delay = delay

    def get_switches(self):
        return [self.left_switch, self.right_switch]

    def get_links(self):
        return [self.link]


class DCFatTree(E2ETopology):

    def __init__(self, basename='', **kwargs):
        self.params = {
            'n_spine_sw': 4,
            'n_agg_bl': 4,
            'n_agg_sw': 4,
            'n_agg_racks': 4,
            'h_per_rack': 40,
            'mtu': '1448',
            'spine_link_delay': '1us',
            'spine_link_rate': '10Gbps',
            'spine_link_queue': '512KB',
            'agg_link_delay': '1us',
            'agg_link_rate': '10Gbps',
            'agg_link_queue': '512KB',
            'sbhost_eth_latency': '500ns',
        }
        for (n,v) in kwargs.items():
            self.params[n] = v

        self.basename = basename

        self.switches = []
        self.spine_switches = []
        self.agg_blocks = []

        self.links = []
        self.spine_agg_links = []
        self.agg_tor_links = []

        self.hosts = []

        self.n_simbricks_host = 0

        bn = basename

        # Create spine switches
        for i in range(0, self.params['n_spine_sw']):
            sw = e2e.E2ESwitchNode(f"_{bn}spine{i}")
            sw.mtu = self.params['mtu']
            self.spine_switches.append(sw)
            self.switches.append(sw)

        # Create aggregation blocks
        for i in range(0, self.params['n_agg_bl']):
            ab = {
                'id': f'agg{i}',
                'switches': [],
                'racks': []
            }

            # Create switches in aggregation blocks
            for j in range(0, self.params['n_agg_sw']):
                sw = e2e.E2ESwitchNode(f"_{bn}agg{i}_{j}")
                sw.mtu = self.params['mtu']
                ab['switches'].append(sw)
                self.switches.append(sw)

            # Create racks (including ToRs)
            for j in range(0, self.params['n_agg_racks']):
                tor = e2e.E2ESwitchNode(f"_{bn}tor{i}_{j}")
                sw.mtu = self.params['mtu']
                r = {
                    'id': f'rack{i}_{j}',
                    'tor': tor,
                    'hosts': []
                }
                ab['racks'].append(r)
                self.switches.append(tor)
            self.agg_blocks.append(ab)

        # wire up switches
        for (i,ab) in enumerate(self.agg_blocks):
            for (j,agg_sw) in enumerate(ab['switches']):
                agg_sw = ab['switches'][j]
                # Wire up aggregation switch to spine switches
                for (si,spine_sw) in enumerate(self.spine_switches):
                    l = e2e.E2ESimpleChannel(f"_{bn}link_sp_ab{i}_as{j}_s{si}")
                    l.left_node = agg_sw
                    l.right_node = spine_sw
                    l.delay = self.params['spine_link_delay']
                    l.data_rate = self.params['spine_link_rate']
                    l.queue_size = self.params['spine_link_queue']
                    self.links.append(l)
                    self.spine_agg_links.append(l)

                # Wire up ToRs to aggregation switches
                for (ti,r) in enumerate(ab['racks']):
                    l = e2e.E2ESimpleChannel(
                            f"_{bn}link_ab{i}_as{j}_tor{ti}")
                    l.left_node = r['tor']
                    l.right_node = agg_sw
                    l.delay = self.params['agg_link_delay']
                    l.data_rate = self.params['agg_link_rate']
                    l.queue_size = self.params['agg_link_queue']
                    self.links.append(l)
                    self.agg_tor_links.append(l)

    def add_to_network(self, net):
        for sw in self.switches:
            net.add_component(sw)
        for l in self.links:
            net.add_component(l)
        #for h in self.hosts:
        #    net.add_component(h)

    def capacity(self):
        max_hs = (self.params['n_agg_bl'] * self.params['n_agg_racks'] *
            self.params['h_per_rack'])
        return max_hs - len(self.hosts)

    def racks_with_capacity(self):
        racks = []
        for (i,ab) in enumerate(self.agg_blocks):
            for (j,r) in enumerate(ab['racks']):
                cap = self.params['h_per_rack'] - len(r['hosts'])
                if cap <= 0:
                    continue
                racks.append((i, j, cap))
        return racks

    def add_host(self, agg, rack, h):
        r = self.agg_blocks[agg]['racks'][rack]
        if len(r['hosts']) >= self.params['h_per_rack']:
            raise BufferError('Requested rack is full')
        r['hosts'].append(h)
        self.hosts.append(h)
        r['tor'].add_component(h)

    def add_host_r(self, h):
        rs = self.racks_with_capacity()
        if not rs:
            raise BufferError('Network is full')
        (agg, rack, _) = random.choice(rs)
        self.add_host(agg, rack, h)
        return (agg, rack)

    def wrap_simbricks_host(self, nic):
        i = self.n_simbricks_host
        self.n_simbricks_host += 1

        host = e2e.E2ESimbricksHost(f'_sbh-{i}-{nic.name}')
        host.eth_latency = self.params['sbhost_eth_latency']
        host.simbricks_component = nic
        return host

    def add_simbricks_host(self, agg, rack, nic):
        self.add_host(agg, rack, self.wrap_simbricks_host(nic))

    def add_simbricks_host_r(self, nic):
        return self.add_host_r(self.wrap_simbricks_host(nic))

    def get_switches(self):
        return self.switches

    def get_links(self):
        return self.links


def add_contig_bg(topo, subnet='10.42.0.0/16', **kwargs):
    params = {
        'link_rate': '1Gbps',
        'link_delay': '1us',
        'link_queue_size': '512KB',
        'congestion_control': e2e.CongestionControl.CUBIC,
        'app_stop_time': '60s',
    }
    for (k,v) in kwargs.items():
        params[k] = v

    pairs = int(topo.capacity() / 2)
    ipn = ipaddress.ip_network(subnet)
    prefix = f'/{ipn.prefixlen}'
    ips = ipn.hosts()
    for i in range(0, pairs):
        s_ip = str(next(ips))
        c_ip = str(next(ips))

        s_host = e2e.E2ESimpleNs3Host(f'bg_s-{i}')
        s_host.delay = params['link_delay']
        s_host.data_rate = params['link_rate']
        s_host.ip = s_ip + prefix
        s_host.queue_size = params['link_queue_size']
        s_host.congestion_control = params['congestion_control']
        s_app = e2e.E2EPacketSinkApplication('sink')
        s_app.local_ip = '0.0.0.0:5000'
        s_app.stop_time = params['app_stop_time']
        s_host.add_component(s_app)
        s_probe = e2e.E2EPeriodicSampleProbe('probe', 'Rx')
        s_probe.interval = '100ms'
        s_probe.file = f'sink-rx-{i}'
        s_app.add_component(s_probe)
        topo.add_host_r(s_host)

        c_host = e2e.E2ESimpleNs3Host(f'bg_c-{i}')
        c_host.delay = params['link_delay']
        c_host.data_rate = params['link_rate']
        c_host.ip = c_ip + prefix
        c_host.queue_size = params['link_queue_size']
        c_host.congestion_control = params['congestion_control']
        c_app = e2e.E2EBulkSendApplication('sender')
        c_app.remote_ip = s_ip + ':5000'
        c_app.stop_time = params['app_stop_time']
        c_host.add_component(c_app)
        topo.add_host_r(c_host)


# Copyright 2024 Max Planck Institute for Software Systems, and
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

import collections
import typing as tp
from enum import Enum
import metis

import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_components as comps
import simbricks.orchestration.e2e_topologies as topos
from simbricks.orchestration.e2e_helpers import E2ELinkAssigner, E2ELinkType

# maps components to consecutive ids and back, ensuring each id is only assigned
# once.
class IDMap(object):
    def __init__(self):
        self.dict = {}
        self.l = []
        self.next = 0

    def to_id(self, n):
        if n in self.dict:
            return self.dict[n]
        else:
            k = self.next
            self.next += 1
            self.dict[n] = k
            self.l.append(n)
            return k

    def from_id(self, i):
        return self.l[i]

    def items(self):
        return self.dict.items()

def parse_duration(s: str) -> float:
    if s.endswith('ps'):
        return float(s[:-2])
    elif s.endswith('ns'):
        return float(s[:-2]) * 1000
    elif s.endswith('us'):
        return float(s[:-2]) * 1000000
    elif s.endswith('ms'):
        return float(s[:-2]) * 1000000000
    else:
        raise ValueError('Unknown duration unit')

def stringify_duration(x: float) -> str:
    if x < 1000:
        return f'{x}ps'
    elif x < 1000000:
        return f'{x / 1000}ns'
    elif x < 1000000000:
        return f'{x / 1000000}us'
    else:
        return f'{x / 1000000000}ms'

def dot_topology(topology, partitions=None):
    if partitions is None:
        partitions = {0: topology.get_switches()}

    dot = 'graph R {\n'
    for p in sorted(partitions.keys()):
        dot += f'subgraph cluster{p} {{\n'
        dot += f'label = "netpart_{p}";\n'
        for n in partitions[p]:
          dot += f'n{n.id} [label="{n.id}"];\n'
        dot += '}\n'
    for l in topology.get_links():
        dot += f'n{l.left_node.id} -- n{l.right_node.id};\n'
    dot += '}'
    return dot

def instantiate_partition(topology, node_partitions, sync_delay_factor=1.0):
    # create the networks
    networks = {}
    mac_start = 0
    switchpart = {}
    for p in sorted(node_partitions.keys()):
        net = sim.NS3E2ENet()
        net.e2e_global.mac_start = mac_start
        mac_start += 10000
        net.name = f'np{p}'
        networks[p] = net

        # add the switches
        for sw in node_partitions[p]:
            switchpart[sw] = p
            net.add_component(sw)

    # add the links
    for i, l in enumerate(topology.get_links()):
        l_p = switchpart[l.left_node]
        r_p = switchpart[l.right_node]
        if l_p == r_p:
            # both end in the same partiton, just add the link
            networks[l_p].add_component(l)
        else:
            # make sure that connections always go in one direction, so there is
            # a topological order for dependencies when launching
            if l_p < r_p:
              lst_p = l_p
              lst = l.left_node
              con_p = r_p
              con = l.right_node
            else:
              lst_p = r_p
              lst = l.right_node
              con_p = l_p
              con = l.left_node

            lst_a = comps.E2ESimbricksNetworkNicIf(
                f'xL_{i}')
            lst_a.eth_latency = f'{l.delay}'
            lst_a.sync_delay = stringify_duration(
                parse_duration(l.delay) * sync_delay_factor)
            lst_a.simbricks_component = networks[con_p]
            lst.add_component(lst_a)

            con_a = comps.E2ESimbricksNetworkNetIf(
                f'xC_{i}')
            con_a.eth_latency = f'{l.delay}'
            con_a.sync_delay = stringify_duration(
                parse_duration(l.delay) * sync_delay_factor)
            con_a.simbricks_component = networks[lst_p]
            con_a.set_peer(lst_a)
            con.add_component(con_a)

    return list(networks.values())


# Split the topology into N networks, return E2ENetwork instances
def partition(topology, N, by_weight=False):
    # Convert topology to adjacency lists for metis solver
    adjlists = collections.defaultdict(tuple)
    idmap = IDMap()
    for l in topology.get_links():
        l_i = idmap.to_id(l.left_node)
        r_i = idmap.to_id(l.right_node)
        adjlists[l_i] += (r_i,)
        adjlists[r_i] += (l_i,)

    max_node = max(adjlists.keys())
    graph = []
    weights = []
    for i in range(0, max_node + 1):
        c = idmap.from_id(i)
        w = c.weight if 'weight' in c.__dict__ else 1
        weights.append(w)
        graph.append(adjlists[i])

    if N == 1:
        # metis does not like N=1 :-)
        parts = [0] * (max_node + 1)
    else:
        if by_weight:
            (edgecuts, parts) = metis.part_graph(graph, N, nodew=weights)
        else:
            (edgecuts, parts) = metis.part_graph(graph, N)

    node_partitions = {}
    for (i,p) in enumerate(parts):
        if p not in node_partitions:
            node_partitions[p] = []
        node_partitions[p].append(idmap.from_id(i))

    return node_partitions


def hier_partitions(topology: topos.DCFatTree):
    partitions = {}

    # trivial partition: all in same partiton
    partitions['s'] = {0: topology.get_switches()}

    # next partition agg blocks (for each agg block, get tors and agg switches)
    aggblocks = []
    for ab in topology.agg_blocks:
        sws = ab['switches'][:]
        for r in ab['racks']:
            sws.append(r['tor'])
        aggblocks.append(sws)

    # one net per aggregation block, spine switches added to first block
    partitions['ab'] = dict((i,j[:]) for i,j in enumerate(aggblocks))
    partitions['ab'][0] += topology.spine_switches

    # one net per AB + one for spine switches
    partitions['ac'] = dict((i,j[:]) for i,j in enumerate(aggblocks))
    partitions['ac'][len(aggblocks)] = topology.spine_switches

    # Next one for core (spine + agg switches), one per rack
    partitions['cr'] = { 0: topology.spine_switches[:] }
    i = 1
    for ab in topology.agg_blocks:
        partitions['cr'][0] += ab['switches']
        for r in ab['racks']:
            partitions['cr'][i] = [r['tor']]
            i += 1

    for k in range(2, topology.params['n_agg_racks'] + 1):
        p = { 0: topology.spine_switches[:] }
        rs = []
        for ab in topology.agg_blocks:
            p[0] += ab['switches']
            for r in ab['racks']:
                rs.append(r['tor'])
        i = 0
        while i * k < len(rs):
            p[i + 1] = rs[i * k: (i+1) * k]
            i += 1
        partitions[f'cr{k}'] = p

    # Fully partitioned one for spine, one per agg-switch, one per rack
    partitions['rs'] = { 0: topology.spine_switches[:] }
    i = 1
    for ab in topology.agg_blocks:
        partitions['rs'][i] = ab['switches']
        i += 1
        for r in ab['racks']:
            partitions['rs'][i] = [r['tor']]
            i += 1
    return partitions

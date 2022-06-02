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

import math
import random
import simbricks.experiments as exp
import simbricks.simulators as sim
import simbricks.proxy as proxy
import simbricks.nodeconfig as node
from simbricks.simulator_utils import create_multinic_hosts

host_types = ['qemu', 'gem5', 'qt']
n_nets = [1, 2, 3, 4, 8, 16, 32]
n_hosts = [2, 10, 20, 30, 35, 40, 50, 60, 70, 80]
experiments = []
separate_net = True

nets_per_host = 2

def select_servers(i, j, racks, n, n_host):
    nc = int(n_host / 2)

    if n == 1:
        # only one network, just connect to all servers
        return racks[i][0]

    all_other_servers = []
    for k in range(0, n):
        if k == i:
            continue
        all_other_servers += racks[k][0]

    n_local = math.ceil(nc / 2)
    n_remote = math.floor(nc / 2)

    servers_local = random.sample(racks[i][0], k=n_local)
    servers_other = random.sample(all_other_servers, k=n_remote)
    return servers_local + servers_other

for host_type in host_types:
  for n in n_nets:
    for n_host in n_hosts:
        random.seed(n + 1000 * n_host)

        nh = math.ceil(n / nets_per_host)
        if separate_net:
            nh += 1

        e = exp.DistributedExperiment(f'dist_memcache-{host_type}-{n}-{n_host}', nh)

        # host
        if host_type == 'qemu':
            host_class = sim.QemuHost
        elif host_type == 'qt':
            def qemu_timing():
                h = sim.QemuHost()
                h.sync = True
                return h
            host_class = qemu_timing
        elif host_type == 'gem5':
            host_class = sim.Gem5Host
            e.checkpoint = False
        else:
            raise NameError(host_type)

        switch_top = sim.SwitchNet()
        switch_top.name = 'switch_top'
        if host_type == 'qemu':
            switch_top.sync = False
        e.add_network(switch_top)
        e.assign_sim_host(switch_top, 0)

        racks = []
        for i in range(0, n):
            h_i = int(i / nets_per_host)
            if separate_net:
                h_i += 1

            switch = sim.SwitchNet()
            switch.name = 'switch_%d' % (i,)
            if host_type == 'qemu':
                switch.sync = False
            e.add_network(switch)
            e.assign_sim_host(switch, h_i)

            switch_top.connect_network(switch)

            # create servers and clients
            m = int(n_host / 2)
            servers = create_multinic_hosts(e, m, 'server_%d' % (i,),
                    switch, host_class, node.I40eLinuxNode,
                    node.MemcachedServer, ip_start = i * n_host + 1,
                    ip_prefix=16)
            for s in servers:
                e.assign_sim_host(s, h_i)
                e.assign_sim_host(s.pcidevs[0].multinic, h_i)

            clients = create_multinic_hosts(e, m, 'client_%d' % (i,),
                    switch, host_class, node.I40eLinuxNode,
                    node.MemcachedClient, ip_start = i * n_host + 1 + m,
                    ip_prefix=16)
            for c in clients:
                c.wait = True
                e.assign_sim_host(c, h_i)
                e.assign_sim_host(c.pcidevs[0].multinic, h_i)

            racks.append((servers, clients))

            if h_i != 0:
                lp = proxy.SocketsNetProxyListener()
                lp.name = 'listener-%d' % (i,)
                e.add_proxy(lp)
                e.assign_sim_host(lp, h_i)

                cp = proxy.SocketsNetProxyConnecter(lp)
                cp.name = 'connecter-%d' % (i,)
                e.add_proxy(cp)
                e.assign_sim_host(cp, 0)

                lp.add_n2n(switch_top, switch)

            for c in clients + servers:
                if host_type == 'qt':
                    c.pcidevs[0].start_tick = 580000000000
                c.extra_deps.append(switch_top)

        all_servers = []
        all_clients = []
        for  (s,c) in racks:
            all_servers += s
            all_clients += c

        # set up client -> server connections
        for i in range(0, n):
            for j in range(0, int(n_host / 2)):
                c = racks[i][1][j]
                servers = select_servers(i, j, racks, n, n_host)
                server_ips = [s.node_config.ip for s in servers]

                c.node_config.app.server_ips = server_ips
                c.node_config.app.threads = len(server_ips)
                c.node_config.app.concurrency = len(server_ips)
                c.extra_deps += all_servers

        for h in all_servers + all_clients:
            h.node_config.disk_image = 'memcached'

        # add to experiments
        experiments.append(e)

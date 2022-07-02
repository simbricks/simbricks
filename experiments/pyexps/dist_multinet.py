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

import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

import simbricks.experiments as exp
from simbricks import proxy

host_types = ['qemu', 'gem5', 'qt']
n_nets = [1, 2, 3, 4]
n_clients = [1, 10, 20, 30, 40, 50]
experiments = []
separate_net = False
separate_server = True

for host_type in host_types:
    for n in n_nets:
        for n_client in n_clients:
            nh = n if not separate_net else n + 1
            e = exp.DistributedExperiment(
                f'dist_multinet-{host_type}-{n}-{n_client}', nh
            )

            # host
            if host_type == 'qemu':
                HostClass = sim.QemuHost
            elif host_type == 'qt':

                def qemu_timing():
                    h = sim.QemuHost()
                    h.sync = True
                    return h

                HostClass = qemu_timing
            elif host_type == 'gem5':
                HostClass = sim.Gem5Host
                e.checkpoint = True
            else:
                raise NameError(host_type)

            switch_top = sim.SwitchNet()
            switch_top.name = 'switch_top'
            if host_type == 'qemu':
                switch_top.sync = False
            e.add_network(switch_top)
            e.assign_sim_host(switch_top, 0)

            for i in range(0, n):
                h_i = i if not separate_net else i + 1
                switch = sim.SwitchNet()
                switch.name = f'switch_{i}'
                if host_type == 'qemu':
                    switch.sync = False
                e.add_network(switch)
                e.assign_sim_host(switch, h_i)

                switch_top.connect_network(switch)

                # create servers and clients
                m = n_client
                if i == 0 or separate_server:
                    servers = create_basic_hosts(
                        e,
                        1,
                        f'server_{i}',
                        switch,
                        sim.I40eNIC,
                        HostClass,
                        node.I40eLinuxNode,
                        node.NetperfServer,
                        ip_start=i * (n_client + 1) + 1
                    )
                    if not separate_server:
                        m = m - 1

                    e.assign_sim_host(servers[0], h_i)
                    e.assign_sim_host(servers[0].pcidevs[0], h_i)

                clients = create_basic_hosts(
                    e,
                    m,
                    f'client_{i}',
                    switch,
                    sim.I40eNIC,
                    HostClass,
                    node.I40eLinuxNode,
                    node.NetperfClient,
                    ip_start=i * (n_client + 1) + 2
                )

                for c in clients:
                    c.wait = True
                    c.node_config.app.server_ip = servers[0].node_config.ip
                    if host_type == 'qemu':
                        c.extra_deps.append(servers[0])

                    e.assign_sim_host(c, h_i)
                    e.assign_sim_host(c.pcidevs[0], h_i)

                if h_i != 0:
                    lp = proxy.SocketsNetProxyListener()
                    lp.name = f'listener-{i}'
                    e.add_proxy(lp)
                    e.assign_sim_host(lp, h_i)

                    cp = proxy.SocketsNetProxyConnecter(lp)
                    cp.name = f'connecter-{i}'
                    e.add_proxy(cp)
                    e.assign_sim_host(cp, 0)

                    lp.add_n2n(switch_top, switch)

                for c in clients + servers:
                    c.pcidevs[0].start_tick = 580000000000

            # add to experiments
            experiments.append(e)

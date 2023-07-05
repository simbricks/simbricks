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
from simbricks.orchestration import proxy
from simbricks.orchestration.simulator_utils import create_basic_hosts

host_types = ['qemu', 'gem5', 'qt']
nic_types = ['i40e', 'cd_bm', 'cd_verilator']
n_clients = [1, 4, 8, 16, 32]
experiments = []

for host_type in host_types:
    for nic_type in nic_types:
        for n in n_clients:
            e = exp.DistributedExperiment(
                f'dist_netperf-{host_type}-{nic_type}-{n}', 2
            )

            net = sim.SwitchNet()
            e.add_network(net)

            # host
            if host_type == 'qemu':
                HostClass = sim.QemuHost
                net.sync = False
            elif host_type == 'qt':

                def qemu_timing(node_config: node.NodeConfig):
                    h = sim.QemuHost(node_config)
                    h.sync = True
                    return h

                HostClass = qemu_timing
            elif host_type == 'gem5':
                HostClass = sim.Gem5Host
                e.checkpoint = True
            else:
                raise NameError(host_type)

            # nic
            if nic_type == 'i40e':
                NicClass = sim.I40eNIC
                NcClass = node.I40eLinuxNode
            elif nic_type == 'cd_bm':
                NicClass = sim.CorundumBMNIC
                NcClass = node.CorundumLinuxNode
            elif nic_type == 'cd_verilator':
                NicClass = sim.CorundumVerilatorNIC
                NcClass = node.CorundumLinuxNode
            else:
                raise NameError(nic_type)

            # create servers and clients
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.NetperfServer
            )

            clients = create_basic_hosts(
                e,
                n,
                'client',
                net,
                NicClass,
                HostClass,
                NcClass,
                node.NetperfClient,
                ip_start=2
            )

            for c in clients:
                c.wait = True
                c.node_config.app.server_ip = servers[0].node_config.ip

            # create proxy
            lp = proxy.SocketsNetProxyListener()
            lp.name = 'listener'
            e.add_proxy(lp)
            cp = proxy.SocketsNetProxyConnecter(lp)
            cp.name = 'connecter'
            e.add_proxy(cp)

            # assign network and server to first host with listener
            e.assign_sim_host(lp, 0)
            e.assign_sim_host(net, 0)
            e.assign_sim_host(servers[0], 0)
            e.assign_sim_host(servers[0].pcidevs[0], 0)
            e.assign_sim_host(cp, 1)

            # round-robin assignment for hosts
            k = 1
            for c in clients:
                e.assign_sim_host(c, k)
                e.assign_sim_host(c.pcidevs[0], k)

                if k != 0:
                    cp.add_nic(c.nics[0])
                k = (k + 1) % 2

            # add to experiments
            experiments.append(e)

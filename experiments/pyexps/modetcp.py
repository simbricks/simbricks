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

# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu/gem5-timing
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: DCTCPm

types_of_host = ['qemu', 'qt', 'gt']
types_of_nic = ['ib', 'cv', 'cb']
types_of_net = ['switch']
types_of_app = ['TCPm']

types_of_num_pairs = [1, 4]
types_of_mode = [0, 1]

experiments = []
for mode in types_of_mode:
    for num_pairs in types_of_num_pairs:

        for host in types_of_host:
            for c in types_of_nic:

                net = sim.SwitchNet()
                net.sync_mode = mode
                #net.opt = link_rate_opt + link_latency_opt

                e = exp.Experiment(
                    f'mode-{mode}-' + host + '-' + c + '-' + 'switch' +
                    f'-{num_pairs}'
                )
                e.add_network(net)

                # host
                if host == 'qemu':
                    HostClass = sim.QemuHost
                elif host == 'qt':

                    def qemu_timing():
                        h = sim.QemuHost()
                        h.sync = True
                        return h

                    HostClass = qemu_timing
                elif host == 'gt':

                    def gem5_timing():
                        h = sim.Gem5Host()
                        return h

                    HostClass = gem5_timing
                    e.checkpoint = True
                else:
                    raise NameError(host)

                # nic

                if c == 'cb':
                    NicClass = sim.CorundumBMNIC
                    NcClass = node.CorundumLinuxNode
                elif c == 'cv':
                    NicClass = sim.CorundumVerilatorNIC
                    NcClass = node.CorundumLinuxNode
                elif c == 'ib':
                    NicClass = sim.I40eNIC
                    NcClass = node.I40eDCTCPNode
                else:
                    raise NameError(c)

                servers = create_basic_hosts(
                    e,
                    num_pairs,
                    'server',
                    net,
                    NicClass,
                    HostClass,
                    NcClass,
                    node.IperfTCPServer
                )
                clients = create_basic_hosts(
                    e,
                    num_pairs,
                    'client',
                    net,
                    NicClass,
                    HostClass,
                    NcClass,
                    node.IperfTCPClient,
                    ip_start=num_pairs + 1
                )

                for se in servers:
                    se.sync_mode = mode
                    se.pcidevs[0].sync_mode = mode

                i = 0
                for cl in clients:
                    cl.sync_mode = mode
                    cl.pcidevs[0].sync_mode = mode
                    cl.node_config.app.server_ip = servers[i].node_config.ip
                    cl.node_config.app.procs = 2
                    i += 1
                    #cl.wait = True

                # All the clients will not poweroff after finishing iperf test
                # except the last one. This is to prevent the simulation gets
                # stuck when one of host exits.

                # The last client waits for the output printed in other hosts,
                # then cleanup.
                clients[num_pairs - 1].node_config.app.is_last = True
                clients[num_pairs - 1].wait = True

                print(e.name)
                experiments.append(e)

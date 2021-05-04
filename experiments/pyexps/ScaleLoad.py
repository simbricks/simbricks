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

import simbricks.experiments as exp
import simbricks.simulators as sim
import simbricks.nodeconfig as node


# iperf UDP Load Scalability test
# naming convention following host-nic-net
# host: gem5-timing
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: UDPs

host_types = ['gt', 'qt', 'qemu']
nic_types = ['cv','cb','ib']
net_types = ['wire', 'sw', 'br']
app = ['UDPs']

rate_types = []
rate_start = 0
rate_end = 1000
rate_step = 100
for r in range(rate_start, rate_end + 1, rate_step):
    rate = f'{r}m'
    rate_types.append(rate)
    

experiments = []

for rate in rate_types:
    for host_type in host_types:
        for nic_type in nic_types:
            for net_type in net_types:

                e = exp.Experiment(host_type + '-' + nic_type + '-' + net_type + '-Load-' + rate )
                # network
                if net_type == 'sw':
                    net = sim.SwitchNet()
                elif net_type == 'br':
                    net = sim.NS3BridgeNet()
                elif net_type == 'wire':
                    net = sim.WireNet()
                else:
                    raise NameError(net_type)
                e.add_network(net)

                # host
                if host_type == 'qemu':
                    host_class = sim.QemuHost
                elif host_type == 'qt':
                    def qemu_timing():
                        h = sim.QemuHost()
                        h.sync = True
                        return h
                    host_class = qemu_timing
                elif host_type == 'gt':
                    host_class = sim.Gem5Host
                    e.checkpoint = True
                else:
                    raise NameError(host_type)

                # nic
                if nic_type == 'ib':
                    nic_class = sim.I40eNIC
                    nc_class = node.I40eLinuxNode
                elif nic_type == 'cb':
                    nic_class = sim.CorundumBMNIC
                    nc_class = node.CorundumLinuxNode
                elif nic_type == 'cv':
                    nic_class = sim.CorundumVerilatorNIC
                    nc_class = node.CorundumLinuxNode
                else:
                    raise NameError(nic_type)

                # create servers and clients
                servers = sim.create_basic_hosts(e, 1, 'server', net, nic_class, host_class,
                        nc_class, node.IperfUDPServer)

                if rate == '0m':
                    clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
                                                     nc_class, node.IperfUDPClientSleep, ip_start=2)
                else:
                    clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
                                                     nc_class, node.IperfUDPClient, ip_start=2)

                clients[0].wait = True
                clients[0].node_config.app.server_ip = servers[0].node_config.ip
                clients[0].node_config.app.is_last = True
                clients[0].node_config.app.rate = rate

                print(e.name)


                # add to experiments
                experiments.append(e)




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
from simbricks.simulator_utils import create_basic_hosts


# iperf TCP_single test
# naming convention following host-nic-net-app
# host: qemu
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: TCPs

kinds_of_host = ['qemu']
kinds_of_nic = ['cv','cb','ib']
kinds_of_net = ['wire', 'switch', 'dumbbell', 'bridge', 'tofino']
kinds_of_app = ['TCPs']

experiments = []

# set network sim
for n in kinds_of_net:
    if n == 'wire':
        net_class = sim.WireNet
    if n == 'switch':
        net_class = sim.SwitchNet
    if n == 'dumbbell':
        net_class = sim.NS3DumbbellNet
    if n == 'bridge':
        net_class = sim.NS3BridgeNet
    if n == 'tofino':
        net_class = sim.TofinoNet


    # set nic sim
    for c in kinds_of_nic:
        net = net_class()
        e = exp.Experiment('qemu-'  + c + '-' + n + '-' + 'TCPs')
        e.add_network(net)

        if c == 'cv':
            servers = create_basic_hosts(e, 1, 'server', net, sim.CorundumVerilatorNIC, sim.QemuHost,
                                             node.CorundumLinuxNode, node.IperfTCPServer)
            clients = create_basic_hosts(e, 1, 'client', net, sim.CorundumVerilatorNIC, sim.QemuHost,
                                             node.CorundumLinuxNode, node.IperfTCPClient, ip_start = 2)


        if c == 'cb':
            servers = create_basic_hosts(e, 1, 'server', net, sim.CorundumBMNIC, sim.QemuHost,
                                             node.CorundumLinuxNode, node.IperfTCPServer)
            clients = create_basic_hosts(e, 1, 'client', net, sim.CorundumBMNIC, sim.QemuHost,
                                             node.CorundumLinuxNode, node.IperfTCPClient, ip_start = 2)



        if c == 'ib':
            servers = create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost,
                                             node.I40eLinuxNode, node.IperfTCPServer)
            clients = create_basic_hosts(e, 1, 'client', net, sim.I40eNIC, sim.QemuHost,
                                             node.I40eLinuxNode, node.IperfTCPClient, ip_start = 2)

        clients[0].wait = True
        clients[0].node_config.app.server_ip = servers[0].node_config.ip

        print(e.name)
        experiments.append(e)


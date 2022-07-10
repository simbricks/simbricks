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
import simbricks.nodeconfig as node
import simbricks.simulators as sim
from simbricks.simulator_utils import create_basic_hosts

# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: TCPm

kinds_of_host = ['qemu']
kinds_of_nic = ['cv', 'cb', 'ib']
kinds_of_net = ['switch', 'dumbbell', 'bridge']
kinds_of_app = ['UDPm']

num_client = 4
rate = '200m'

experiments = []

# set network sim
for n in kinds_of_net:

    if n == 'switch':
        NetClass = sim.SwitchNet
    if n == 'dumbbell':
        NetClass = sim.NS3DumbbellNet
    if n == 'bridge':
        NetClass = sim.NS3BridgeNet

    # set nic sim
    for c in kinds_of_nic:
        net = NetClass()
        e = exp.Experiment('qemu-' + c + '-' + n + '-' + 'UDPm')
        e.add_network(net)

        if c == 'cv':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.CorundumVerilatorNIC,
                sim.QemuHost,
                node.CorundumLinuxNode,
                node.IperfUDPServer
            )
            clients = create_basic_hosts(
                e,
                num_client,
                'client',
                net,
                sim.CorundumVerilatorNIC,
                sim.QemuHost,
                node.CorundumLinuxNode,
                node.IperfUDPClient,
                ip_start=2
            )

        if c == 'cb':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.CorundumBMNIC,
                sim.QemuHost,
                node.CorundumLinuxNode,
                node.IperfUDPServer
            )
            clients = create_basic_hosts(
                e,
                num_client,
                'client',
                net,
                sim.CorundumBMNIC,
                sim.QemuHost,
                node.CorundumLinuxNode,
                node.IperfUDPClient,
                ip_start=2
            )

        if c == 'ib':
            servers = create_basic_hosts(
                e,
                1,
                'server',
                net,
                sim.I40eNIC,
                sim.QemuHost,
                node.I40eLinuxNode,
                node.IperfUDPServer
            )
            clients = create_basic_hosts(
                e,
                num_client,
                'client',
                net,
                sim.I40eNIC,
                sim.QemuHost,
                node.I40eLinuxNode,
                node.IperfUDPClient,
                ip_start=2
            )

        for cl in clients:
            cl.wait = True
            cl.node_config.app.server_ip = servers[0].node_config.ip
            cl.node_config.app.rate = rate

        print(e.name)
        experiments.append(e)

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


e = exp.Experiment('qemu-e1000-pair')
net = sim.SwitchNet()
e.add_network(net)

servers = create_basic_hosts(e, 1, 'server', net, sim.E1000NIC, sim.QemuHost,
        node.E1000LinuxNode, node.IperfTCPServer)

clients = create_basic_hosts(e, 1, 'client', net, sim.E1000NIC, sim.QemuHost,
        node.E1000LinuxNode, node.IperfTCPClient, ip_start = 2)

for c in clients:
    c.wait = True
    c.node_config.app.server_ip = servers[0].node_config.ip

experiments = [e]


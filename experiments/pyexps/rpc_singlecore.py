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


msg_sizes = [64, 1024, 8092]
stacks = ['mtcp', 'tas', 'linux']
num_clients = 1

experiments = []
for msg_size in msg_sizes:
  for stack in stacks:
    e = exp.Experiment('qemu-ib-switch-rpc-%s-1t-1fpc-%db-0mpc' % (stack,msg_size))
    net = sim.SwitchNet()
    e.add_network(net)

    if stack == 'tas':
        n = node.TASNode
    elif stack == 'mtcp':
        n = node.MtcpNode
    else:
        n = node.I40eLinuxNode

    servers = create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost,
            n, node.RPCServer)

    clients = create_basic_hosts(e, num_clients, 'client', net, sim.I40eNIC,
            sim.QemuHost, n, node.RPCClient, ip_start = 2)

    for h in servers + clients:
        h.node_config.cores = 1 if stack != 'tas' else 3
        h.node_config.fp_cores = 1
        h.node_config.app.threads = 1
        h.node_config.app.max_bytes = msg_size

        if stack == 'linux':
            h.node_config.disk_image = 'tas'

    servers[0].sleep = 5

    for c in clients:
        c.wait = True
        c.node_config.app.server_ip = servers[0].node_config.ip

    experiments.append(e)


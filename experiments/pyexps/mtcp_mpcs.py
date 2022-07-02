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

mpcs = [1, 8, 128]
stacks = ['linux', 'mtcp']
server_cores = 8
client_cores = 4
num_clients = 4
connections = 512
msg_size = 64

experiments = []
for mpc in mpcs:
    for stack in stacks:
        e = exp.Experiment(f'qemu-ib-switch-mtcp_mpc-P{stack}-{mpc}')
        e.timeout = 5 * 60
        # add meta data for output file
        e.metadata['mpc'] = mpc
        e.metadata['stack'] = stack

        net = sim.SwitchNet()
        e.add_network(net)

        if stack == 'tas':
            N = node.TASNode
        elif stack == 'mtcp':
            N = node.MtcpNode
        else:
            N = node.I40eLinuxNode

        servers = create_basic_hosts(
            e, 1, 'server', net, sim.I40eNIC, sim.QemuHost, N, node.RPCServer
        )

        clients = create_basic_hosts(
            e,
            num_clients,
            'client',
            net,
            sim.I40eNIC,
            sim.QemuHost,
            N,
            node.RPCClient,
            ip_start=2
        )

        for h in servers:
            h.node_config.cores = server_cores
            h.node_config.app.threads = server_cores
            h.node_config.app.max_flows = connections * 4
            h.sleep = 5

        for c in clients:
            c.wait = True
            c.node_config.cores = client_cores
            c.node_config.app.threads = client_cores

            c.node_config.app.server_ip = servers[0].node_config.ip
            c.node_config.app.max_msgs_conn = mpc
            c.node_config.app.max_flows = \
                int(connections / num_clients / client_cores)

        for h in servers + clients:
            h.node_config.app.max_bytes = msg_size

            if stack == 'linux':
                h.node_config.disk_image = 'tas'
            elif stack == 'tas':
                h.node_config.cores += 2
                h.node_config.fp_cores = 1
        experiments.append(e)

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

configs = [
    (node.I40eLinuxNode, node.HTTPDLinux, node.HTTPCLinux, 'linux'),
    (node.I40eLinuxNode, node.HTTPDLinuxRPO, node.HTTPCLinux, 'linuxrpo'),
    (node.MtcpNode, node.HTTPDMtcp, node.HTTPCMtcp, 'mtcp')
    ]

server_cores = 1
client_cores = 1
num_clients = 1
connections = 1024
file_size = 64

experiments = []

for (nodec, appc, clientc, label) in configs:
    e = exp.Experiment('qemu-ib-switch-mtcp_httpd-%s' % (label))
    e.timeout = 5* 60

    net = sim.SwitchNet()
    e.add_network(net)

    servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC,
            sim.QemuHost, nodec, appc)

    clients = sim.create_basic_hosts(e, num_clients, 'client', net, sim.I40eNIC,
            sim.QemuHost, nodec, clientc, ip_start = 2)

    for h in servers:
        h.node_config.cores = server_cores
        h.node_config.app.threads = server_cores
        h.node_config.app.file_size = file_size
        h.sleep = 10

    for c in clients:
        c.node_config.cores = client_cores
        c.node_config.app.threads = client_cores
        c.node_config.app.server_ip = servers[0].node_config.ip
        c.node_config.app.max_msgs_conn = 0
        c.node_config.app.max_flows = \
            int(connections / num_clients)
    clients[-1].wait = True

    for h in servers + clients:
        h.node_config.disk_image = 'mtcp'
    experiments.append(e)


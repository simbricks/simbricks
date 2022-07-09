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

host_types = ['gt']
nic_types = ['ib']
net_types = ['sw']

num_cores = 1
n_client = 1

experiments = []

e = exp.Experiment('dt-gt-ib-sw')
net = sim.SwitchNet()
e.add_network(net)
host_class = sim.Gem5Host
e.checkpoint = False

nic_class = sim.I40eNIC
nc_class = node.I40eLinuxNode

# create a host
servers = create_basic_hosts(
    e,
    1,
    'server',
    net,
    nic_class,
    host_class,
    nc_class,
    node.IperfUDPServer,
    ip_start=2
)

servers[0].node_config.nockp = 1
servers[0].variant = 'opt'
servers[0].cpu_freq = '3GHz'
servers[0].extra_main_args = [
    '--debug-flags=SimBricksSync,SimBricksPci,SimBricksEthernet'
]
# create a host
clients = create_basic_hosts(
    e,
    1,
    'client',
    net,
    nic_class,
    host_class,
    nc_class,
    node.IperfUDPShortClient,
    ip_start=2
)

clients[0].cpu_freq = '3GHz'
clients[0].variant = 'opt'
clients[0].node_config.cores = num_cores
clients[0].node_config.app.is_sleep = 1
clients[0].node_config.nockp = 1
clients[0].node_config.app.is_last = True
clients[0].extra_main_args = [
    '--debug-flags=SimBricksSync,SimBricksPci,SimBricksEthernet'
]
clients[0].wait = True

print(e.name)

# add to experiments
experiments.append(e)

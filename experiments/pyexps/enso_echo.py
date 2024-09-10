# Copyright (c) 2021-2024, Max Planck Institute for Software Systems,
# National University of Singapore, and Carnegie Mellon University
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
"""Experiment, which simulates two hosts with Enso one running an echo server
and the other EnsoGen."""

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
from simbricks.orchestration.simulator_utils import create_basic_hosts


class EnsoLocal(node.EnsoNode):

    def __init__(self):
        super().__init__()
        self.local_enso_dir = None

        # Uncomment to specify a local Enso directory to copy to the node.
        # self.local_enso_dir = "/enso"


class ConfiguredEnsoGen(node.EnsoGen):

    def __init__(self):
        super().__init__()
        self.count = 1000  # Number of packets to send.


experiments = []

e = exp.Experiment('echo-qemu-switch-enso_bm')

net = sim.SwitchNet()
net.sync = False

e.add_network(net)

servers = create_basic_hosts(
    e,
    1,
    'server',
    net,
    sim.EnsoBMNIC,
    sim.QemuHost,
    EnsoLocal,
    node.EnsoEchoServer
)

clients = create_basic_hosts(
    e,
    1,
    'client',
    net,
    sim.EnsoBMNIC,
    sim.QemuHost,
    EnsoLocal,
    ConfiguredEnsoGen,
    ip_start=2
)

for c in clients:
    c.wait = True

experiments.append(e)

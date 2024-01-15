# Copyright 2023 Max Planck Institute for Software Systems, and
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

import random
import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim
import simbricks.orchestration.e2e_components as e2e
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts
from simbricks.orchestration.e2e_topologies import (
    DCFatTree, add_contig_bg
)

random.seed(42)

e = exp.Experiment('e2e_bg')

options = {
    'ns3::TcpSocket::SegmentSize': '1448',
    'ns3::TcpSocket::SndBufSize': '524288',
    'ns3::TcpSocket::RcvBufSize': '524288',
    'ns3::Ipv4GlobalRouting::RandomEcmpRouting': '1',
}

topology = DCFatTree(
            n_spine_sw=2,
            n_agg_bl=2,
            n_agg_sw=1,
            n_agg_racks=2,
            h_per_rack=1,
        )
add_contig_bg(topology)

net = sim.NS3E2ENet()
net.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])
net.add_component(topology)
net.wait = True
e.add_network(net)

experiments = [e]

# Copyright 2024 Max Planck Institute for Software Systems, and
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
import simbricks.orchestration.e2e_partition as e2e_part
from simbricks.orchestration.simulator_utils import create_tcp_cong_hosts
from simbricks.orchestration.e2e_topologies import (
    DCFatTree, add_contig_bg
)



sync_factors = [1.0, 0.5, 0.25, 0.1]
options = {
    'ns3::TcpSocket::SegmentSize': '1448',
    'ns3::TcpSocket::SndBufSize': '524288',
    'ns3::TcpSocket::RcvBufSize': '524288',
}

kinds_of_parts = e2e_part.hier_partitions(DCFatTree()).keys()

experiments = []
for p in kinds_of_parts:
  for sf in sync_factors:
    e = exp.Experiment(f'e2e_bgsplit-{p}-{sf}')
    # Make sure background hosts are placed the same way
    random.seed(42)

    # Create empty topology first
    topology = DCFatTree()
    # fill up with background traffic hosts
    add_contig_bg(topology)

    partition = e2e_part.hier_partitions(topology)[p]
    nets = e2e_part.instantiate_partition(topology, partition, sf)
    dot = e2e_part.dot_topology(topology, partition)
    for net in nets:
      net.e2e_global.stop_time = '50ms'
      net.opt = ' '.join([f'--{o[0]}={o[1]}' for o in options.items()])
      net.wait = True
      e.add_network(net)
      net.init_network()

    with open(f'out/{e.name}.dot', 'w') as f:
      f.write(dot)

    experiments.append(e)

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

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as nodec
import simbricks.orchestration.simulators as sim

experiments = []


class MemTest(nodec.AppConfig):

    def __init__(self, addr):
        self.addr = addr

    def run_cmds(self, node):
        return [
            f'busybox devmem 0x{self.addr:x} 64 0x1234567834567890',
            f'busybox devmem 0x{self.addr:x} 64',
            f'busybox devmem 0x{self.addr:x} 64 0x9876543276543210',
            f'busybox devmem 0x{self.addr:x} 64'
        ]


for h in ['gk', 'simics']:
    e = exp.Experiment('basicmem-' + h)
    e.checkpoint = False

    mem = sim.BasicMemDev()
    mem.name = 'mem0'
    mem.addr = 0x2000000000  #0x2000000000000000

    node_config = nodec.NodeConfig()
    node_config.nockp = True
    node_config.app = MemTest(mem.addr)

    if h == 'gk':
        host = sim.Gem5Host(node_config)
        host.cpu_type = 'X86KvmCPU'
        host.variant = 'opt'
    elif h == 'qk':
        host = sim.QemuHost(node_config)
    elif h == 'simics':
        host = sim.SimicsHost(node_config)
        host.sync = True
        e.checkpoint = True
    else:
        raise NameError(h)

    host.name = 'host.0'
    e.add_host(host)
    host.wait = True

    e.add_memdev(mem)

    host.add_memdev(mem)

    experiments.append(e)

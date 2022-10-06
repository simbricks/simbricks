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
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim

experiments = []
num_mem_lat = [500, 100, 20]  #ns
num_netmem = 5
num_hosts = 20


class MemTest(node.AppConfig):

    def __init__(
        self,
        disagg_addr: int,
        idx: int,
        disagg_size: int,
        disaggregated: bool,
        time_limit: int
    ):
        self.disagg_addr = disagg_addr
        self.idx = idx
        self.disagg_size = disagg_size
        self.disaggregated = disaggregated
        self.time_limit = time_limit

    def config_files(self):
        # pylint: disable-next=consider-using-with
        m = {'farmem.ko': open('../images/farmem/farmem.ko', 'rb')}
        return {**m, **super().config_files()}

    def run_cmds(self, _):
        commands = []
        commands.append(
            f'busybox devmem 0x{self.disagg_addr:x} 64 0x{42 + self.idx} '
        )
        commands.append(f'busybox devmem 0x{self.disagg_addr:x} 64')

        return commands


far_mem_size = 1024 * 1024 * 1024
half_far_mem_size = 512 * 1024 * 1024
# AS_ID, VADDR_START(include), VADDR_END(not include), MEMNODE_MAC, PHYS_START
sw_mem_map = [
    (19, half_far_mem_size, far_mem_size, '00:00:00:00:00:15', 0),
    (0, 0, far_mem_size, '00:00:00:00:00:15', half_far_mem_size),
    (1, 0, far_mem_size, '00:00:00:00:00:15', half_far_mem_size + far_mem_size),
    (
        2,
        0,
        far_mem_size,
        '00:00:00:00:00:15',
        half_far_mem_size + 2 * far_mem_size
    ),
    (
        3,
        0,
        half_far_mem_size,
        '00:00:00:00:00:15',
        half_far_mem_size + 3 * far_mem_size
    ),
    (3, half_far_mem_size, far_mem_size, '00:00:00:00:00:16', 0),
    (4, 0, far_mem_size, '00:00:00:00:00:16', half_far_mem_size),
    (5, 0, far_mem_size, '00:00:00:00:00:16', half_far_mem_size + far_mem_size),
    (
        6,
        0,
        far_mem_size,
        '00:00:00:00:00:16',
        half_far_mem_size + 2 * far_mem_size
    ),
    (
        7,
        0,
        half_far_mem_size,
        '00:00:00:00:00:16',
        half_far_mem_size + 3 * far_mem_size
    ),
    (7, half_far_mem_size, far_mem_size, '00:00:00:00:00:17', 0),
    (8, 0, far_mem_size, '00:00:00:00:00:17', half_far_mem_size),
    (9, 0, far_mem_size, '00:00:00:00:00:17', half_far_mem_size + far_mem_size),
    (
        10,
        0,
        far_mem_size,
        '00:00:00:00:00:17',
        half_far_mem_size + 2 * far_mem_size
    ),
    (
        11,
        0,
        half_far_mem_size,
        '00:00:00:00:00:17',
        half_far_mem_size + 3 * far_mem_size
    ),
    (11, half_far_mem_size, far_mem_size, '00:00:00:00:00:18', 0),
    (12, 0, far_mem_size, '00:00:00:00:00:18', half_far_mem_size),
    (
        13,
        0,
        far_mem_size,
        '00:00:00:00:00:18',
        half_far_mem_size + far_mem_size
    ),
    (
        14,
        0,
        far_mem_size,
        '00:00:00:00:00:18',
        half_far_mem_size + 2 * far_mem_size
    ),
    (
        15,
        0,
        half_far_mem_size,
        '00:00:00:00:00:18',
        half_far_mem_size + 3 * far_mem_size
    ),
    (15, half_far_mem_size, far_mem_size, '00:00:00:00:00:19', 0),
    (16, 0, far_mem_size, '00:00:00:00:00:19', half_far_mem_size),
    (
        17,
        0,
        far_mem_size,
        '00:00:00:00:00:19',
        half_far_mem_size + far_mem_size
    ),
    (
        18,
        0,
        far_mem_size,
        '00:00:00:00:00:19',
        half_far_mem_size + 2 * far_mem_size
    ),
    (
        19,
        0,
        half_far_mem_size,
        '00:00:00:00:00:19',
        half_far_mem_size + 3 * far_mem_size
    ),
]

for mem_lat in num_mem_lat:
    for h in ['gk', 'gt']:
        e = exp.Experiment('memswl-' + h + f'-{mem_lat}')
        e.checkpoint = True

        # Add three MemNics for each host
        mems = []
        for i in range(num_hosts):
            mem = sim.MemNIC()
            mem.name = 'mem' + f'{i}'
            mem.addr = 0x2000000000  #0x2000000000000000
            mem.mac = '00:00:00:00:00:' + f'{(i + 1):x}'
            mem.as_id = i
            mem.sync_period = mem_lat
            mem.mem_latency = mem_lat
            mems.append(mem)

        # Add two NetMes
        netmems = []
        for i in range(num_netmem):
            netmem = sim.NetMem()
            netmem.mac = '00:00:00:00:00:' + f'{(20 + i + 1):x}'
            netmem.name = 'netmem' + f'{i}'
            netmem.size = 0x100000000  # 4GB per netmems
            netmems.append(netmem)

        ###
        node_configs = []
        for i in range(num_hosts):
            nc = node.NodeConfig()
            nc.kcmd_append += 'numa=fake=2'
            nc.app = MemTest(mems[i].addr, 0, mems[i].size, True, 1)
            node_configs.append(nc)

        net = sim.MemSwitchNet()
        for tp in sw_mem_map:
            net.mem_map.append(tp)

        e.add_network(net)

        if h == 'gk':

            def gem5_kvm(node_config: node.NodeConfig):
                gh = sim.Gem5Host(node_config)
                gh.cpu_type = 'X86KvmCPU'
                gh.variant = 'opt'
                return gh

            HostClass = gem5_kvm

        if h == 'gt':

            def gem5_timing(node_config: node.NodeConfig):
                gh = sim.Gem5Host(node_config)
                gh.cpu_type = 'TimingSimpleCPU'
                gh.variant = 'opt'
                return gh

            HostClass = gem5_timing

        elif h == 'qk':
            HostClass = sim.QemuHost

        # Add hosts
        hosts = []
        for i in range(num_hosts):
            host = HostClass(node_configs[i])
            host.name = 'host.' + f'{i}'
            host.wait = True
            e.add_host(host)
            hosts.append(host)

        for i in range(num_hosts):
            mems[i].set_network(net)
            e.add_memdev(mems[i])
            hosts[i].add_memdev(mems[i])

        for i in range(num_netmem):
            netmems[i].set_network(net)

        experiments.append(e)

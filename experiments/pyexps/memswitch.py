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
num_of_netmem =[1, 2, 3, 4]
num_mem_lat = [500, 100, 20] #ns

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
        m = {'farmem.ko': open('../images/farmem/farmem.ko', 'rb')}
        return {**m, **super().config_files()}

    def run_cmds(self, node):
        commands = [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'free -m',
            (
                f'insmod /tmp/guest/farmem.ko base_addr=0x{self.disagg_addr:x} '
                f'size=0x{self.disagg_size:x} nnid=1 drain_node=1'
            ),
            'free -m',
            'numactl -H',
            (
                f'numactl --membind={1 if self.disaggregated else 0} '
                'sysbench '
                f'--time={self.time_limit} '
                '--validate=on '
                '--histogram=on '
                'memory '
                '--memory-oper=write '
                '--memory-block-size=16M '
                '--memory-access-mode=rnd '
                '--memory-total-size=0 run'
            )
        ]

        # for addr in self.addr:
        #     commands.append(f'busybox devmem 0x{addr:x} 64 0x{42 + self.idx} ')
        #     commands.append(f'busybox devmem 0x{addr:x} 64')

        return commands

# host 0 <-> memnic 0 \         / netmem 0
# host 1 <-> memnic 1 -  Switch 
# host 2 <-> memnic 2 /         \ netmem 1
#
# [netmem 0] and [netmem 1] each has 2 GB memory.
# each host has 1 GB of far memory.
# [host 0] only uses [netmem 0], [host 1] only uses [netmem 1]
# [host 2] has 512 MB at [netmem 0] and 512 MB at [netmem 1] 

# AS_ID,    VADDR_START(include),V  ADDR_END(not include),  MEMNODE_MAC,    PHYS_START
sw_mem_map = [(0, 0, 1024*1024*1024, '00:00:00:00:00:04', 0),
            (1, 0, 1024*1024*1024, '00:00:00:00:00:05', 0),
            (2, 0, 512*1024*1024, '00:00:00:00:00:04', 1024*1024*1024),
            (2, 512*1024*1024, 1024*1024*1024, '00:00:00:00:00:05', 1024*1024*1024)]

for mem_lat in num_mem_lat:
    for h in ['gk', 'gt']:
        e = exp.Experiment('memsw-' + h + f'-{mem_lat}')
        e.checkpoint = True

        # Add three MemNics for each host
        mem0 = sim.MemNIC()
        mem0.name = 'mem0'
        mem0.addr = 0x2000000000 #0x2000000000000000
        mem0.mac = '00:00:00:00:00:01'
        mem0.as_id = 0
        mem0.sync_period = mem_lat
        mem0.mem_latency = mem_lat

        mem1 = sim.MemNIC()
        mem1.name = 'mem1'
        mem1.addr = 0x2000000000 #0x2000000000000000
        mem1.mac = '00:00:00:00:00:02'
        mem1.as_id = 1
        mem1.sync_period = mem_lat
        mem1.mem_latency = mem_lat

        mem2 = sim.MemNIC()
        mem2.name = 'mem2'
        mem2.addr = 0x2000000000 #0x2000000000000000
        mem2.mac = '00:00:00:00:00:03'
        mem2.as_id = 2
        mem2.sync_period = mem_lat
        mem2.mem_latency = mem_lat

        # Add two NetMes
        netmem0 = sim.NetMem()
        netmem0.mac = '00:00:00:00:00:04'
        netmem0.name = 'netmem0'
        netmem0.size = 0x80000000

        netmem1 = sim.NetMem()
        netmem1.mac = '00:00:00:00:00:05'
        netmem1.name = 'netmem1'
        netmem1.size = 0x80000000

        ###
        node_config0 = node.NodeConfig()
        node_config0.kcmd_append += 'numa=fake=2'
        #node_config0.nockp = True
        node_config0.app = MemTest(mem0.addr, 0, mem0.size, True, 1)

        node_config1 = node.NodeConfig()
        node_config1.kcmd_append += 'numa=fake=2'
        #node_config1.nockp = True
        node_config1.app = MemTest(mem1.addr, 1, mem1.size, True, 1)

        node_config2 = node.NodeConfig()
        node_config2.kcmd_append += 'numa=fake=2'
        #node_config2.nockp = True
        node_config2.app = MemTest(mem2.addr, 2, mem2.size, True, 1)

        net = sim.MemSwitchNet()
        for tp in sw_mem_map:
            net.mem_map.append(tp)

        e.add_network(net)

        if h == 'gk':
            def gem5_kvm(node_config: node.NodeConfig):
                h = sim.Gem5Host(node_config)
                h.cpu_type = 'X86KvmCPU'
                h.variant = 'opt'
                return h
            HostClass = gem5_kvm

        if h == 'gt':
            def gem5_timing(node_config: node.NodeConfig):
                h = sim.Gem5Host(node_config)
                h.cpu_type = 'TimingSimpleCPU'
                h.variant = 'opt'
                return h
            HostClass = gem5_timing

        elif h == 'qk':
            HostClass = sim.QemuHost
        
        # Add hosts
        host_0 = HostClass(node_config0)
        host_1 = HostClass(node_config1)
        host_2 = HostClass(node_config2)
    
        host_0.name = 'host.0'
        host_1.name = 'host.1'
        host_2.name = 'host.2'

        e.add_host(host_0)
        e.add_host(host_1)
        e.add_host(host_2)

        host_0.wait = True
        host_1.wait = True
        host_2.wait = True

        mem0.set_network(net)
        mem1.set_network(net)
        mem2.set_network(net)
        e.add_memdev(mem0)
        e.add_memdev(mem1)
        e.add_memdev(mem2)

        host_0.add_memdev(mem0)
        host_1.add_memdev(mem1)
        host_2.add_memdev(mem2)

        netmem0.set_network(net)
        netmem1.set_network(net)


        experiments.append(e)

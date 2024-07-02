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
"""
Runs sysbench memory benchmarks for different memory configurations.

Used to compare latency and throughput of disaggregated memory to local one.
"""

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim

host_types = ['gem5', 'simics']
mem_types = ['local', 'basicmem']
experiments = []


class SysbenchMemoryBenchmark(node.AppConfig):

    def __init__(
        self,
        disagg_addr: int,
        disagg_size: int,
        disaggregated: bool,
        time_limit: int,
        num_threads=1
    ):
        self.disagg_addr = disagg_addr
        """Address of disaggregated memory start."""
        self.disagg_size = disagg_size
        """Size of disaggregated memory."""
        self.disaggregated = disaggregated
        """Whether to use disaggregated memory."""
        self.time_limit = time_limit
        """
        Time limit for sysbench benchmark in seconds.

        0 to disable limit.
        """
        self.num_threads = num_threads
        """Number of cores to run the benchmark on in parallel."""

    # pylint: disable=consider-using-with
    def config_files(self):
        m = {'farmem.ko': open('../images/farmem/farmem.ko', 'rb')}
        return {**m, **super().config_files()}

    def run_cmds(self, _):
        cmds = [
            'mount -t proc proc /proc', 'mount -t sysfs sysfs /sys', 'free -m'
        ]
        if self.disaggregated:
            cmds.append(
                f'insmod /tmp/guest/farmem.ko '
                f'base_addr=0x{self.disagg_addr:x} '
                f'size=0x{self.disagg_size:x} nnid=1 drain_node=1'
            )
            cmds.append('free -m')
            cmds.append('numactl -H')

        sysbench_cmd = (
            'sysbench '
            f'--time={self.time_limit} '
            '--histogram=on '
            'memory '
            '--memory-oper=read '
            '--memory-block-size=16M '
            '--memory-access-mode=rnd '
            '--memory-total-size=0 run'
        )

        parallel_cmd = str()
        for i in range(self.num_threads):
            parallel_cmd += (
                f'numactl --membind={1 if self.disaggregated else 0} '
                f'--physcpubind={i} {sysbench_cmd} & '
            )
        parallel_cmd += 'wait'
        cmds.append(parallel_cmd)

        return cmds


# Create multiple experiments with different simulator permutations, which can
# be filtered later.
for host_type in host_types:
    for mem_type in mem_types:
        e = exp.Experiment(f'sysbench_memory-{host_type}-{mem_type}')

        if not mem_type in mem_types:
            raise NameError(mem_type)

        mem = sim.BasicMemDev()
        mem.name = 'mem0'
        mem.addr = 0x2000000000

        # node config
        node_config = node.NodeConfig()
        node_config.cores = 1
        node_config.threads = 1
        node_config.memory = 4096
        # TODO Simics offers no way to extend the kernel command line. Instead,
        # the base image has to be rebuilt to set the following option using
        # GRUB in `images/scripts/install-base.sh`.
        if host_type != 'simics':
            node_config.kcmd_append += 'numa=fake=2'

        # app config
        app = SysbenchMemoryBenchmark(
            mem.addr,
            mem.size,
            mem_type == 'basicmem',
            1,
            node_config.cores * node_config.threads
        )
        node_config.app = app

        # host
        if host_type == 'gem5':
            host = sim.Gem5Host(node_config)
            e.checkpoint = True
        elif host_type == 'simics':
            host = sim.SimicsHost(node_config)
            host.sync = True
            host.timing = True
            e.checkpoint = True
        else:
            raise NameError(host_type)

        host.name = 'host.0'
        e.add_host(host)
        host.wait = True
        host.mem_latency = host.sync_period = mem.mem_latency = \
            mem.sync_period = 500

        if mem_type == 'basicmem':
            host.add_memdev(mem)
            e.add_memdev(mem)

        # add to experiments
        experiments.append(e)

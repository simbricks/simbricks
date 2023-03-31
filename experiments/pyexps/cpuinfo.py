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
"""Runs /proc/cpuinfo in the host simulator to determine available CPU
features."""

import typing as tp

import simbricks.orchestration.experiments as exp
import simbricks.orchestration.nodeconfig as node
import simbricks.orchestration.simulators as sim

host_types = ['gem5', 'simics', 'qemu']
experiments = []


class Cpuinfo(node.AppConfig):

    def run_cmds(self, _: node.NodeConfig) -> tp.List[str]:
        return ['mount -t proc proc /proc', 'cat /proc/cpuinfo']


# Create multiple experiments with different simulator permutations, which can
# be filtered later.
for host_type in host_types:
    e = exp.Experiment(f'cpuinfo-{host_type}')

    node_config = node.NodeConfig()
    node_config.app = Cpuinfo()

    # host
    if host_type == 'gem5':
        host = sim.Gem5Host(node_config)
        e.checkpoint = True
    elif host_type == 'simics':
        host = sim.SimicsHost(node_config)
        host.sync = True
        e.checkpoint = True
    elif host_type == 'qemu':
        host = sim.QemuHost(node_config)
        host.sync = True
    else:
        raise NameError(host_type)

    host.name = 'host.0'
    e.add_host(host)
    host.wait = True

    # add to experiments
    experiments.append(e)

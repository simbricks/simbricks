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

host_configs = ['qemu', 'gt', 'qt']
seq_configs = ['swseq', 'ehseq', 'tofino']
nic_configs = ['ib', 'cb', 'cv']
proto_configs = ['vr', 'nopaxos']
num_client_configs = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
experiments = []
sync_period = 200

link_rate_opt = '--LinkRate=100Gb/s '  # don't forget space at the end
link_latency_opt = '--LinkLatency=500ns '

for proto_config in proto_configs:
    for num_c in num_client_configs:
        for host_config in host_configs:
            for seq_config in seq_configs:
                for nic_config in nic_configs:
                    e = exp.Experiment(
                        proto_config + '-' + host_config + '-' + nic_config +
                        '-' + seq_config + f'-{num_c}'
                    )
                    if seq_config == 'tofino':
                        net = sim.TofinoNet()
                    else:
                        net = sim.NS3SequencerNet()
                    net.sync_period = sync_period
                    net.opt = link_rate_opt + link_latency_opt
                    e.add_network(net)

                    # host
                    if host_config == 'qemu':
                        host_class = sim.QemuHost
                        net.sync = False
                    elif host_config == 'gt':
                        host_class = sim.Gem5Host
                        e.checkpoint = True
                    elif host_config == 'qt':

                        def qemu_timing():
                            h = sim.QemuHost()
                            h.sync = True
                            return h

                        host_class = qemu_timing
                    else:
                        raise NameError(host_config)

                    # nic
                    if nic_config == 'ib':
                        nic_class = sim.I40eNIC
                        nc_class = node.I40eLinuxNode
                    elif nic_config == 'cb':
                        nic_class = sim.CorundumBMNIC
                        nc_class = node.CorundumLinuxNode
                    elif nic_config == 'cv':
                        nic_class = sim.CorundumVerilatorNIC
                        nc_class = node.CorundumLinuxNode
                    else:
                        raise NameError(nic_config)

                    # app
                    if proto_config == 'vr':
                        replica_class = node.VRReplica
                        client_class = node.VRClient
                    elif proto_config == 'nopaxos':
                        replica_class = node.NOPaxosReplica
                        client_class = node.NOPaxosClient
                    else:
                        raise NameError(proto_config)

                    # endhost sequencer
                    if seq_config == 'ehseq' and proto_config == 'nopaxos':
                        sequencer = create_basic_hosts(
                            e,
                            1,
                            'sequencer',
                            net,
                            nic_class,
                            host_class,
                            nc_class,
                            node.NOPaxosSequencer,
                            ip_start=100
                        )
                        sequencer[0].node_config.disk_image = 'nopaxos'
                        sequencer[0].pcidevs[0].sync_period = sync_period
                        sequencer[0].sync_period = sync_period

                    replicas = create_basic_hosts(
                        e,
                        3,
                        'replica',
                        net,
                        nic_class,
                        host_class,
                        nc_class,
                        replica_class
                    )
                    for i in range(len(replicas)):
                        replicas[i].node_config.app.index = i
                        replicas[i].node_config.disk_image = 'nopaxos'
                        replicas[i].pcidevs[0].sync_period = sync_period
                        replicas[i].sync_period = sync_period

                    clients = create_basic_hosts(
                        e,
                        num_c,
                        'client',
                        net,
                        nic_class,
                        host_class,
                        nc_class,
                        client_class,
                        ip_start=4
                    )

                    for c in clients:
                        c.node_config.app.server_ips = [
                            '10.0.0.1', '10.0.0.2', '10.0.0.3'
                        ]
                        if seq_config == 'ehseq':
                            c.node_config.app.server_ips.append('10.0.0.100')
                            c.node_config.app.use_ehseq = True
                        c.node_config.disk_image = 'nopaxos'
                        c.pcidevs[0].sync_period = sync_period
                        c.sync_period = sync_period

                    clients[num_c - 1].wait = True
                    clients[num_c - 1].node_config.app.is_last = True

                    #print(e.name)

                    experiments.append(e)

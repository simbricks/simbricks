import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

host_configs = ['qemu', 'gt']
seq_configs = ['swseq', 'ehseq']
nic_configs = ['ib', 'cb', 'cv']
experiments = []

link_rate_opt = '--LinkRate=100Gb/s ' # don't forget space at the end
link_latency_opt = '--LinkLatency=500ns '

for host_config in host_configs:
    for seq_config in seq_configs:
        for nic_config in nic_configs:
            e = exp.Experiment('nopaxos-' + host_config + '-' + nic_config + '-' + seq_config)
            net = sim.NS3SequencerNet()
            net.opt = link_rate_opt + link_latency_opt
            e.add_network(net)

            # host
            if host_config == 'qemu':
                host_class = sim.QemuHost
                # nic
                if nic_config == 'ib':
                    nic_class = sim.I40eNIC
                    nc_class = node.I40eLinuxNode
                elif nic_config == 'cb':
                    nic_class = sim.CorundumBMNIC
                    nc_class = node.CorundumLinuxNode
                else:
                    continue
                
            elif host_config == 'gt':
                host_class = sim.Gem5Host
                e.checkpoint = False
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
            else:
                raise NameError(host_config)


            nc_class.disk_image = 'nopaxos'

            if seq_config == 'ehseq':
                sequencer = sim.create_basic_hosts(e, 1, 'sequencer', net, nic_class,
                        host_class, nc_class, node.NOPaxosSequencer, ip_start = 100)
                sequencer[0].sleep = 1

            replicas = sim.create_basic_hosts(e, 3, 'replica', net, nic_class,
                    host_class, nc_class, node.NOPaxosReplica)
            for i in range(len(replicas)):
                replicas[i].node_config.app.index = i
                replicas[i].sleep = 1

            clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class,
                    host_class, nc_class, node.NOPaxosClient, ip_start = 4)
            for c in clients:
                c.node_config.app.server_ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
                c.wait = True

            experiments.append(e)

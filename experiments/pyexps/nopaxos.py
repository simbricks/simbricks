import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

host_configs = ['qemu', 'gt']
seq_configs = ['swseq', 'ehseq']
nic_configs = ['ib', 'cb', 'cv']
proto_configs = ['vr', 'nopaxos']
num_client_configs = [1, 2, 3, 4]
experiments = []

link_rate_opt = '--LinkRate=100Gb/s ' # don't forget space at the end
link_latency_opt = '--LinkLatency=500ns '

for proto_config in proto_configs:
    for num_c in num_client_configs:
        for host_config in host_configs:
            for seq_config in seq_configs:
                for nic_config in nic_configs:
                    e = exp.Experiment(proto_config + '-'  + host_config + '-' + nic_config + '-' + seq_config + f'-{num_c}')
                    net = sim.NS3SequencerNet()
                    net.opt = link_rate_opt + link_latency_opt
                    e.add_network(net)

                    # host
                    if host_config == 'qemu':
                        host_class = sim.QemuHost
                    elif host_config == 'gt':
                        host_class = sim.Gem5Host
                        e.checkpoint = False
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

                    nc_class.disk_image = 'nopaxos'

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
                        sequencer = sim.create_basic_hosts(e, 1, 'sequencer', net, nic_class,
                                host_class, nc_class, node.NOPaxosSequencer, ip_start = 100)
                        sequencer[0].sleep = 1

                    replicas = sim.create_basic_hosts(e, 3, 'replica', net, nic_class,
                            host_class, nc_class, replica_class)
                    for i in range(len(replicas)):
                        replicas[i].node_config.app.index = i
                        replicas[i].sleep = 1

                    clients = sim.create_basic_hosts(e, num_c, 'client', net, nic_class,
                            host_class, nc_class, client_class, ip_start = 4)

                    for c in clients:
                        c.node_config.app.server_ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

                    clients[num_c - 1].wait = True
                    clients[num_c - 1].sleep = 5

                    print(e.name)
                    #print (len(experiments))

                    experiments.append(e)


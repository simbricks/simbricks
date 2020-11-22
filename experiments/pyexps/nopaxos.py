import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

host_configs = ['bm', 'cycle']
seq_configs = ['swseq', 'ehseq']
experiments = []

for host_config in host_configs:
    for seq_config in seq_configs:
        e = exp.Experiment('nopaxos-' + host_config + '-' + seq_config)
        net = sim.NS3SequencerNet()
        e.add_network(net)

        if host_config == 'bm':
            host_class = sim.QemuHost
            nic_class = sim.CorundumBMNIC
            nc_class = node.CorundumLinuxNode
        elif host_config == 'cycle':
            host_class = sim.Gem5Host
            nic_class = sim.CorundumVerilatorNIC
            nc_class = node.CorundumLinuxNode
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

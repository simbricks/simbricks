import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

class NOPaxosNodeConfig(node.CorundumLinuxNode):
    disk_image = 'nopaxos'

config = ['swseq', 'ehseq']
experiments = []

for c in config:
    e = exp.Experiment('qemu-nopaxos-' + c)
    net = sim.NS3SequencerNet()
    e.add_network(net)

    if c == 'ehseq':
        sequencer = sim.create_basic_hosts(e, 1, 'sequencer', net, sim.CorundumBMNIC,
                sim.QemuHost, NOPaxosNodeConfig, node.NOPaxosSequencer, ip_start = 100)
        sequencer[0].sleep = 1

    replicas = sim.create_basic_hosts(e, 3, 'replica', net, sim.CorundumBMNIC,
            sim.QemuHost, NOPaxosNodeConfig, node.NOPaxosReplica)
    for i in range(len(replicas)):
        replicas[i].node_config.app.index = i
        replicas[i].sleep = 1

    clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumBMNIC,
            sim.QemuHost, NOPaxosNodeConfig, node.NOPaxosClient, ip_start = 4)
    for c in clients:
        c.node_config.app.server_ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
        c.wait = True

    experiments.append(e)

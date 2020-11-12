import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

e = exp.Experiment('qemu-nopaxos-ehseq')
net = sim.NS3SequencerNet()
e.add_network(net)

class NOPaxosHost(sim.QemuHost):
    disk_image = 'nopaxos'

sequencer = sim.create_basic_hosts(e, 1, 'sequencer', net, sim.CorundumBMNIC, NOPaxosHost,
        node.CorundumLinuxNode, node.NOPaxosSequencer, ip_start = 100)
replicas = sim.create_basic_hosts(e, 3, 'replica', net, sim.CorundumBMNIC, NOPaxosHost,
        node.CorundumLinuxNode, node.NOPaxosReplica)
clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumBMNIC, NOPaxosHost,
        node.CorundumLinuxNode, node.NOPaxosClient, ip_start = 4)

sequencer[0].sleep = 1

for i in range(len(replicas)):
    replicas[i].node_config.app.index = i
    replicas[i].sleep = 1

for c in clients:
    c.node_config.app.server_ips = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
    c.wait = True

experiments = [e]

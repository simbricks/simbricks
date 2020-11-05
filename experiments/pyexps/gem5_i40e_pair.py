import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

e = exp.Experiment('gem5-i40e-pair')
#e.timeout = 5 * 60
e.checkpoint = True
net = sim.SwitchNet()
e.add_network(net)

servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.Gem5Host,
        node.I40eLinuxNode, node.IperfTCPServer)

clients = sim.create_basic_hosts(e, 2, 'client', net, sim.I40eNIC, sim.Gem5Host,
        node.I40eLinuxNode, node.IperfTCPClient, ip_start = 2)

for h in servers + clients:
    h.cpu_type = 'TimingSimpleCPU'
    h.cpu_type_cp = 'TimingSimpleCPU'

for c in clients:
    c.wait = True
    c.node_config.app.server_ip = servers[0].node_config.ip

experiments = [e]

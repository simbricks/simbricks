import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


e = exp.Experiment('qemu-i40e-pair')
net = sim.SwitchNet()
e.add_network(net)

servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost,
        node.I40eLinuxNode, node.IperfTCPServer)

clients = sim.create_basic_hosts(e, 2, 'client', net, sim.I40eNIC, sim.QemuHost,
        node.I40eLinuxNode, node.IperfTCPClient, ip_start = 2)

for c in clients:
    c.wait = True
    c.node_config.app.server_ip = servers[0].node_config.ip

experiments = [e]


import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

e = exp.Experiment('qemu-i40e-pair')
net = sim.SwitchNet()
e.add_network(net)

nic_a = sim.I40eNIC()
nic_a.set_network(net)
e.add_nic(nic_a)

host_a = sim.QemuHost()
host_a.name = 'server'
host_a.node_config = node.I40eLinuxNode()
host_a.node_config.ip = '10.0.0.1'
host_a.node_config.app = node.IperfTCPServer()
host_a.add_nic(nic_a)
e.add_host(host_a)

for i in range (0, 2):
    nic_b = sim.I40eNIC()
    nic_b.set_network(net)
    e.add_nic(nic_b)

    host_b = sim.QemuHost()
    host_b.name = 'client.%d' % i
    host_b.wait = True
    host_b.node_config = node.I40eLinuxNode()
    host_b.node_config.ip = '10.0.0.%d' % (2 + i)
    host_b.node_config.app = node.IperfTCPClient()
    host_b.add_nic(nic_b)
    e.add_host(host_b)

env = exp.ExpEnv('..', './work')
out = exp.run_exp_local(e, env)
print(out.dumps())

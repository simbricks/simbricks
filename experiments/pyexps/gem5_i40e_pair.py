import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

e = exp.Experiment('gem5-i40e-pair')
e.timeout = 5 * 60
e.checkpoint = True
net = sim.SwitchNet()
e.add_network(net)

nic_a = sim.I40eNIC()
nic_a.set_network(net)
e.add_nic(nic_a)

host_a = sim.Gem5Host()
host_a.cpu_type = 'X86KvmCPU'
host_a.name = 'server'
host_a.node_config = node.I40eLinuxNode()
host_a.node_config.sim = 'gem5' # FIXME
host_a.node_config.ip = '10.0.0.1'
host_a.node_config.app = node.IperfTCPServer()
host_a.add_nic(nic_a)
e.add_host(host_a)

for i in range (0, 1):
    nic_b = sim.I40eNIC()
    nic_b.set_network(net)
    e.add_nic(nic_b)

    host_b = sim.Gem5Host()
    host_b.cpu_type = 'X86KvmCPU'
    host_b.name = 'client.%d' % i
    host_b.wait = True
    host_b.node_config = node.I40eLinuxNode()
    host_b.node_config.sim = 'gem5' # FIXME
    host_b.node_config.ip = '10.0.0.%d' % (2 + i)
    host_b.node_config.app = node.IperfTCPClient()
    host_b.add_nic(nic_b)
    e.add_host(host_b)

experiments = [e]


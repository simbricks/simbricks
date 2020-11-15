import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_single test
# naming convention following host-nic-net-app
# host: qemu
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: TCPs

kinds_of_host = ['qemu']
kinds_of_nic = ['cv','cb','ib']
#kinds_of_nic = ['ib']
kinds_of_net = ['wire', 'switch', 'dumbbell', 'bridge']
kinds_of_app = ['TCPs']

experiments = []

# set network sim
for n in kinds_of_net:
    if n == 'wire':
        net_class = sim.WireNet
    if n == 'switch':
        net_class = sim.SwitchNet
    if n == 'dumbbell':
        net_class = sim.NS3DumbbellNet
    #if n == 'bridge':
        # net = sim.NS3BridgeNet()
        #continue


    # set nic sim
    for c in kinds_of_nic:
        net = net_class()
        e = exp.Experiment('qemu-'  + c + '-' + n + '-' + 'TCPs')
        e.add_network(net)
        
        if c == 'cv':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumVerilatorNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfTCPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumVerilatorNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfTCPClient, ip_start = 2)

        
        if c == 'cb':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumBMNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfTCPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumBMNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfTCPClient, ip_start = 2)
            
        

        if c == 'ib':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost, 
                                             node.I40eLinuxNode, node.IperfTCPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.I40eNIC, sim.QemuHost, 
                                             node.I40eLinuxNode, node.IperfTCPClient, ip_start = 2)
            
        clients[0].wait = True
        clients[0].node_config.app.server_ip = servers[0].node_config.ip

        print(e.name)
        experiments.append(e)


"""
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
"""

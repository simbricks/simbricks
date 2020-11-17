import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_single test
# naming convention following host-nic-net-app
# host: gem5-timing
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: UDPs

kinds_of_host = ['gem5-timing']
kinds_of_nic = ['cv','cb','ib']
kinds_of_net = ['wire', 'switch', 'dumbbell', 'bridge']
kinds_of_app = ['UDPs']

rate = '200m'

experiments = []

# set network sim
for n in kinds_of_net:
    if n == 'wire':
        net_class = sim.WireNet
    if n == 'switch':
        net_class = sim.SwitchNet
    if n == 'dumbbell':
        net_class = sim.NS3DumbbellNet
    if n == 'bridge':
        net_class = sim.NS3BridgeNet


    # set nic sim
    for c in kinds_of_nic:
        net = net_class()
        e = exp.Experiment('gt-'  + c + '-' + n + '-' + 'UDPs')
        e.checkpoint = True
        e.add_network(net)
        
        if c == 'cv':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumVerilatorNIC, sim.Gem5Host, 
                                             node.CorundumLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumVerilatorNIC, sim.Gem5Host, 
                                             node.CorundumLinuxNode, node.IperfUDPClient, ip_start = 2)

        
        if c == 'cb':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumBMNIC, sim.Gem5Host, 
                                             node.CorundumLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.CorundumBMNIC, sim.Gem5Host, 
                                             node.CorundumLinuxNode, node.IperfUDPClient, ip_start = 2)
            
        

        if c == 'ib':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.Gem5Host, 
                                             node.I40eLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, 1, 'client', net, sim.I40eNIC, sim.Gem5Host, 
                                             node.I40eLinuxNode, node.IperfUDPClient, ip_start = 2)
            
        clients[0].wait = True
        clients[0].node_config.app.server_ip = servers[0].node_config.ip
        clients[0].node_config.app.rate = rate

        print(e.name)
        experiments.append(e)


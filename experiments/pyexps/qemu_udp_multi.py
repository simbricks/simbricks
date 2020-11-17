import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: TCPm

kinds_of_host = ['qemu']
kinds_of_nic = ['cv','cb','ib']
kinds_of_net = ['switch', 'dumbbell', 'bridge']
kinds_of_app = ['UDPm']

num_client = 4
rate = '200m'

experiments = []

# set network sim
for n in kinds_of_net:

    if n == 'switch':
        net_class = sim.SwitchNet
    if n == 'dumbbell':
        net_class = sim.NS3DumbbellNet
    if n == 'bridge':
        net_class = sim.NS3BridgeNet


    # set nic sim
    for c in kinds_of_nic:
        net = net_class()
        e = exp.Experiment('qemu-'  + c + '-' + n + '-' + 'UDPm')
        e.add_network(net)
        
        if c == 'cv':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumVerilatorNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, num_client, 'client', net, sim.CorundumVerilatorNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfUDPClient, ip_start = 2)

        
        if c == 'cb':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.CorundumBMNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, num_client, 'client', net, sim.CorundumBMNIC, sim.QemuHost, 
                                             node.CorundumLinuxNode, node.IperfUDPClient, ip_start = 2)
            
        

        if c == 'ib':
            servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost, 
                                             node.I40eLinuxNode, node.IperfUDPServer)
            clients = sim.create_basic_hosts(e, num_client, 'client', net, sim.I40eNIC, sim.QemuHost, 
                                             node.I40eLinuxNode, node.IperfUDPClient, ip_start = 2)
            
        
        for cl in clients:
            cl.wait = True
            cl.node_config.app.server_ip = servers[0].node_config.ip
            cl.node_config.app.rate = rate

        print(e.name)
        experiments.append(e)


import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

host_configs = ['bm', 'cycle']
n_clients = [1, 2, 4, 8]
target_bandwidth = 100

experiments = []

for host_config in host_configs:
    for nc in n_clients:
        e = exp.Experiment('scalability-' + host_config + '-' + str(nc))

        if host_config == 'bm':
            host_class = sim.QemuHost
            nic_class = sim.CorundumBMNIC
            nc_class = node.CorundumLinuxNode
            net = sim.SwitchNet()
        elif host_config == 'cycle':
            host_class = sim.Gem5Host
            nic_class = sim.CorundumVerilatorNIC
            nc_class = node.CorundumLinuxNode
            net = sim.NS3BridgeNet()
        else:
            raise NameError(host_config)

        e.add_network(net)

        servers = sim.create_basic_hosts(e, 1, 'server', net, nic_class, host_class,
                nc_class, node.IperfUDPServer)

        clients = sim.create_basic_hosts(e, nc, 'client', net, nic_class, host_class,
                nc_class, node.IperfUDPClient)

        for c in clients:
            c.wait = True
            c.node_config.app.server_ip = servers[0].node_config.ip
            c.node_config.app.rate = str(target_bandwidth/nc)+'m'

        experiments.append(e)

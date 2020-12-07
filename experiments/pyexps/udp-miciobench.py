import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_single test
# naming convention following host-nic-net-app
# host: gem5-timing
# nic:  cv/cb/ib
# net:  wire/switch/dumbbell/bridge
# app: UDPs

host_types = ['gt', 'qt', 'qemu']
nic_types = ['cv','cb','ib']
net_types = ['switch', 'bridge']
app = ['UDPmicro']

total_rate = 1000 # Mbps
num_client_max = 8
num_client_step = 2
num_client_types = [1, 3, 7, 15, 31]
#for n in range(1, num_client_max + 1, num_client_step):
#    num_client_types.append(n)
#    print(n)




experiments = []

for n_client in num_client_types:

    per_client_rate = int(total_rate/n_client)
    rate = f'{per_client_rate}m'

    for host_type in host_types:
        for nic_type in nic_types:
            for net_type in net_types:

                e = exp.Experiment(host_type + '-' + nic_type + '-' + net_type + '-UDPmicro-' + f'{total_rate}' + f'-{n_client}')
                # network
                if net_type == 'switch':
                    net = sim.SwitchNet()
                elif net_type == 'bridge':
                    net = sim.NS3BridgeNet()
                else:
                    raise NameError(net_type)
                e.add_network(net)

                # host
                if host_type == 'qemu':
                    host_class = sim.QemuHost
                elif host_type == 'qt':
                    def qemu_timing():
                        h = sim.QemuHost()
                        h.sync = True
                        return h
                    host_class = qemu_timing
                elif host_type == 'gt':
                    host_class = sim.Gem5Host
                    e.checkpoint = True
                else:
                    raise NameError(host_type)

                # nic
                if nic_type == 'ib':
                    nic_class = sim.I40eNIC
                    nc_class = node.I40eLinuxNode
                elif nic_type == 'cb':
                    nic_class = sim.CorundumBMNIC
                    nc_class = node.CorundumLinuxNode
                elif nic_type == 'cv':
                    nic_class = sim.CorundumVerilatorNIC
                    nc_class = node.CorundumLinuxNode
                else:
                    raise NameError(nic_type)

                # create servers and clients
                servers = sim.create_basic_hosts(e, 1, 'server', net, nic_class, host_class,
                        nc_class, node.IperfUDPServer)

                
                clients = sim.create_basic_hosts(e, n_client, 'client', net, nic_class, host_class,
                                                 nc_class, node.IperfUDPClient, ip_start=2)

                clients[n_client-1].node_config.app = node.IperfUDPClientLast()
                clients[n_client-1].wait = True

                for c in clients:
                    c.node_config.app.server_ip = servers[0].node_config.ip
                    c.node_config.app.rate = rate


                print(e.name)


                # add to experiments
                experiments.append(e)




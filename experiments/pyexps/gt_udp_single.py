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
net_types = ['wire', 'switch', 'bridge']
app = ['UDPs']

rate_types = []
rate_start = 0
rate_end = 140
rate_step = 20
for r in range(rate_start, rate_end + 1, rate_step):
    rate = f'{r}m'
    rate_types.append(rate)
    

experiments = []

for rate in rate_types:
    for host_type in host_types:
        for nic_type in nic_types:
            for net_type in net_types:

                e = exp.Experiment(host_type + '-' + nic_type + '-' + net_type + '-UDPs-' + rate )
                # network
                if net_type == 'switch':
                    net = sim.SwitchNet()
                elif net_type == 'bridge':
                    net = sim.NS3BridgeNet()
                elif net_type == 'wire':
                    net = sim.WireNet()
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
                    e.checkpoint = False
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

                if rate == '0m':
                    clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
                                                     nc_class, node.IperfUDPClientSleep, ip_start=2)
                else:
                    clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
                                                     nc_class, node.IperfUDPClient, ip_start=2)

                clients[0].wait = True
                clients[0].node_config.app.server_ip = servers[0].node_config.ip
                clients[0].node_config.app.rate = rate

                print(e.name)


                # add to experiments
                experiments.append(e)




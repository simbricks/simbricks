import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node

host_types = ['qemu', 'gem5']
nic_types = ['i40e', 'cd_bm', 'cd_verilator']
net_types = ['switch', 'ns3']
experiments = []

for host_type in host_types:
    for nic_type in nic_types:
        for net_type in net_types:
            e = exp.Experiment('netperf-' + host_type + '-' + net_type + '-' + nic_type)

            # network
            if net_type == 'switch':
                net = sim.SwitchNet()
            elif net_type == 'ns3':
                net = sim.NS3BridgeNet()
            else:
                raise NameError(net_type)
            e.add_network(net)

            # host
            if host_type == 'qemu':
                host_class = sim.QemuHost
            elif host_type == 'gem5':
                host_class = sim.Gem5Host
            else:
                raise NameError(host_type)

            # nic
            if nic_type == 'i40e':
                nic_class = sim.I40eNIC
                nc_class = node.I40eLinuxNode
            elif nic_type == 'cd_bm':
                nic_class = sim.CorundumBMNIC
                nc_class = node.CorundumLinuxNode
            elif nic_type == 'cd_verilator':
                nic_class = sim.CorundumVerilatorNIC
                nc_class = node.CorundumLinuxNode
            else:
                raise NameError(nic_type)

            # create servers and clients
            servers = sim.create_basic_hosts(e, 1, 'server', net, nic_class, host_class,
                    nc_class, node.NetperfServer)

            clients = sim.create_basic_hosts(e, 1, 'client', net, nic_class, host_class,
                    nc_class, node.NetperfClient, ip_start = 2)

            for c in clients:
                c.wait = True
                c.node_config.app.server_ip = servers[0].node_config.ip

            # add to experiments
            experiments.append(e)

import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu/gem5-timing
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: DCTCPm

types_of_host = ['qemu', 'qt','gt']
types_of_nic = ['cv','cb']
types_of_net = ['switch']
types_of_app = ['TCPm']


types_of_num_pairs = [1, 4]
types_of_mode = [0, 1]


experiments = []
for mode in types_of_mode:
    for num_pairs in types_of_num_pairs:
        
        for h in types_of_host:
            for c in types_of_nic:

                net = sim.SwitchNet()
                net.sync_mode = mode
                #net.opt = link_rate_opt + link_latency_opt

                e = exp.Experiment( f'modetcp-{mode}-' + h + '-' + c + '-' + 'switch' + f'-{num_pairs}')
                e.add_network(net)

                # host
                if h == 'qemu':
                    host_class = sim.QemuHost
                elif h == 'qt':
                    def qemu_timing():
                        h = sim.QemuHost()
                        h.sync = True
                        return h
                    host_class = qemu_timing
                elif h == 'gt':
                    def gem5_timing():
                        h = sim.Gem5Host()
                        return h
                    host_class = gem5_timing
                    e.checkpoint = True
                else:
                    raise NameError(h)

                # nic
                
                if c == 'cb':
                    nic_class = sim.CorundumBMNIC
                    nc_class = node.CorundumLinuxNode
                elif c == 'cv':
                    nic_class = sim.CorundumVerilatorNIC
                    nc_class = node.CorundumLinuxNode
                else:
                    raise NameError(c)


                servers = sim.create_basic_hosts(e, num_pairs, 'server', net, nic_class, host_class, 
                                                nc_class, node.IperfTCPServer)
                clients = sim.create_basic_hosts(e, num_pairs, 'client', net, nic_class, host_class, 
                                                nc_class, node.IperfTCPClient, ip_start=num_pairs+1)

                for se in servers:
                    se.sync_mode = mode
                    se.nics[0].sync_mode = mode

                
                

                i = 0
                for cl in clients:
                    cl.sync_mode = mode
                    cl.nics[0].sync_mode = mode
                    cl.node_config.app.server_ip = servers[i].node_config.ip
                    cl.node_config.app.procs = 2
                    i += 1
                    #cl.wait = True
                
                # All the clients will not poweroff after finishing iperf test except the last one
                # This is to prevent the simulation gets stuck when one of host exits.

                # The last client waits for the output printed in other hosts, then cleanup
                clients[num_pairs-1].node_config.app.is_last = True
                clients[num_pairs-1].wait = True

                print(e.name)
                experiments.append(e)


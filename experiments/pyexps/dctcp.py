import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


# iperf TCP_multi_client test
# naming convention following host-nic-net-app
# host: qemu/gem5-timing
# nic:  cv/cb/ib
# net:  switch/dumbbell/bridge
# app: DCTCPm

types_of_host = ['qemu', 'qt','gt', 'gO3']
types_of_nic = ['cv','cb','ib']
types_of_net = ['dumbbell']
types_of_app = ['DCTCPm']
types_of_mtu = [1500, 4000, 9000]

num_pairs = 2
max_k = 199680
k_step = 8320
#k_step = 16640
link_rate_opt = '--LinkRate=10Gb/s ' # don't forget space at the end
link_latency_opt = '--LinkLatency=500ns '
cpu_freq = '5GHz' #GHz
#mtu = 4000
sys_clock = '2GHz' # if not set, default 1GHz

ip_start = '192.168.64.1'

experiments = []

# set network sim
net_class = sim.NS3DumbbellNet

for mtu in types_of_mtu:
    for h in types_of_host:
        for c in types_of_nic:
            for k_val in range(0, max_k + 1, k_step):

                net = net_class()
                net.opt = link_rate_opt + link_latency_opt + f'--EcnTh={k_val}'

                e = exp.Experiment( h + '-' + c + '-' + 'dumbbell' + '-' + 'DCTCPm' + f'{k_val}' + f'-{mtu}')
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
                    host_class = sim.Gem5Host
                    host_class.sys_clock = sys_clock
                    e.checkpoint = True
                elif h == 'gO3':
                    host_class = sim.Gem5Host
                    host_class.cpu_type = 'DerivO3CPU' 
                    host_class.sys_clock = sys_clock
                    e.checkpoint = True
                else:
                    raise NameError(h)

                # nic
                if c == 'ib':
                    nic_class = sim.I40eNIC
                    nc_class = node.I40eDCTCPNode
                elif c == 'cb':
                    nic_class = sim.CorundumBMNIC
                    nc_class = node.CorundumDCTCPNode
                elif c == 'cv':
                    nic_class = sim.CorundumVerilatorNIC
                    nc_class = node.CorundumDCTCPNode
                else:
                    raise NameError(c)


                servers = sim.create_dctcp_hosts(e, num_pairs, 'server', net, nic_class, host_class, 
                                                nc_class, node.DctcpServer, cpu_freq, mtu)
                clients = sim.create_dctcp_hosts(e, num_pairs, 'client', net, nic_class, host_class, 
                                                nc_class, node.DctcpClient, cpu_freq, mtu, ip_start=num_pairs+1)

            
                i = 0
                for cl in clients:
                    cl.node_config.app.server_ip = servers[i].node_config.ip
                    i += 1
                
                # All the clients will not poweroff after finishing iperf test except the last one
                # This is to prevent the simulation gets stuck when one of host exits.

                # The last client waits for the output printed in other hosts, then cleanup
                clients[num_pairs-1].node_config.app.is_last = True
                clients[num_pairs-1].wait = True

                print(e.name)
                experiments.append(e)


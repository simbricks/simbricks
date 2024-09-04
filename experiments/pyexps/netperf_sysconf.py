
import simbricks.orchestration.system as system
import simbricks.orchestration.simulation as sim
import simbricks.orchestration.instantiation as inst
"""
Netperf Example:
One Client: Host_0, One Server: Host1 connected through a switch
HOST0 -- NIC0 ------ SWITCH ------ NIC1 -- HOST1

This scripts generates the experiments with all the combinations of different execution modes
"""

# host_types = ['qemu', 'gem5', 'qt']
host_types = ['gem5']
nic_types = ['bm']
net_types = ['switch']
experiments = []

sys = system.System()

# create a host instance and a NIC instance then install the NIC on the host
host0 = system.I40ELinuxHost(sys)
pcie0 = system.PCIeHostInterface(host0)
host0.add_if(pcie0)
nic0 = system.IntelI40eNIC(sys)
nic0.add_ipv4('10.0.0.1')
pcichannel0 = system.PCIeChannel(pcie0, nic0.pci_if)

# create a host instance and a NIC instance then install the NIC on the host
host1 = system.I40ELinuxHost(sys)
pcie1 = system.PCIeHostInterface(host1)
host1.add_if(pcie0)
nic1 = system.IntelI40eNIC(sys)
nic1.add_ipv4('10.0.0.2')
pcichannel1 = system.PCIeChannel(pcie1, nic1.pci_if)

'''
port0 = spec.NetDev()
port1 = spec.NetDev()
switch = spec.Switch(system)
switch.install_netdev(port0)
switch.install_netdev(port1)

ethchannel0 = spec.Eth(system)
ethchannel0.install(nic0, port0)
ethchannel1 = spec.Eth(system)
ethchannel1.install(nic1, port1)

# configure the software to run on the host
host0.app = spec.NetperfClient('10.0.0.2')
host1.app = spec.NetperfServer()

"""
Execution Config
"""
for host_type in host_types:
    for nic_type in nic_types:
        for net_type in net_types:
            e = exp.Experiment(
                'n-' + host_type + '-' + nic_type + '-' + net_type
            )
            allobj = runobj.AllObj()

            # Host
            if host_type == 'gem5':
                host_sim = impl.Gem5Sim
            elif host_type == 'qemu':

                def qemu_sim(e):
                    h = impl.QemuSim(e)
                    h.sync = False
                    return h
                host_sim = qemu_sim

            elif host_type == 'qt':
                host_sim = impl.QemuSim
            else:
                raise NameError(host_type)
            
            # NIC
            if nic_type == 'bm':
                nic_sim = impl.CorundumBMNICSim
            elif nic_type == 'vr':
                nic_sim = impl.CorundumVerilatorNICSim
            else:
                raise NameError(nic_type)

            # Net
            if net_type == 'switch':
                net_sim = impl.SwitchBMSim
            else:
                raise NameError(net_type)


            host_inst0 = host_sim(e, allobj)
            host_inst0.add(host0)

            host_inst1 = host_sim(e, allobj)
            host_inst1.add(host1)

            nic_inst0 = nic_sim(e, allobj)
            nic_inst0.add(nic0)

            nic_inst1 = nic_sim(e, allobj)
            nic_inst1.add(nic1)

            net_inst = net_sim(e, allobj)
            net_inst.add(switch)
            
            print(e.name + "   all simulators:")
            sims = e.all_simulators()
            for sim in sims:
                print(sim)

            experiments.append(e)
        '''
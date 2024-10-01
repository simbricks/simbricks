from simbricks.orchestration import system
from simbricks.orchestration import simulation as sim
from simbricks.orchestration import instantiation as inst
from simbricks.orchestration.helpers import simulation as sim_helpers

"""
Netperf Example:
One Client: Host_0, One Server: Host1 connected through a switch
HOST0 -- NIC0 ------ SWITCH ------ NIC1 -- HOST1

This scripts generates the experiments with all the combinations of different execution modes
"""

host_types = ["gem5"]
nic_types = ["i40e"]
net_types = ["switch"]
experiments = []

sys = system.System()

# create a host instance and a NIC instance then install the NIC on the host
# host0 = system.CorundumLinuxHost(sys)
host0 = system.I40ELinuxHost(sys)
pcie0 = system.PCIeHostInterface(host0)
cfg_disk0 = system.DistroDiskImage(h=host0, name="base")
host0.add_disk(cfg_disk0)
tar_disk0 = system.LinuxConfigDiskImage(h=host0)
host0.add_disk(tar_disk0)

host0.add_if(pcie0)
# nic0 = system.CorundumNIC(sys)
nic0 = system.IntelI40eNIC(sys)
nic0.add_ipv4("10.0.0.1")
pcichannel0 = system.PCIeChannel(pcie0, nic0._pci_if)

# create a host instance and a NIC instance then install the NIC on the host
host1 = system.I40ELinuxHost(sys)
pcie1 = system.PCIeHostInterface(host1)
cfg_disk1 = system.DistroDiskImage(h=host1, name="base")
host1.add_disk(cfg_disk1)
tar_disk1 = system.LinuxConfigDiskImage(h=host1)
host1.add_disk(tar_disk1)

host1.add_if(pcie1)
nic1 = system.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
pcichannel1 = system.PCIeChannel(pcie1, nic1._pci_if)

# # create switch and its ports
# switch = system.EthSwitch(sys)
# netif0 = system.EthInterface(switch)
# switch.add_if(netif0)
# netif1 = system.EthInterface(switch)
# switch.add_if(netif1)
# # create channels and connect the switch to the host nics
# ethchannel0 = system.EthChannel(switch.eth_ifs[0], nic0._eth_if)
# ethchannel1 = system.EthChannel(switch.eth_ifs[1], nic1._eth_if)

switch0 = system.EthSwitch(sys)
switch1 = system.EthSwitch(sys)
# connect first switch to client nic
switch0_for_nic = system.EthInterface(switch0)
switch0.add_if(switch0_for_nic)
nic0_switch0_chan = system.EthChannel(nic0._eth_if, switch0_for_nic)
# connect second switch to server nic
switch1_for_nic = system.EthInterface(switch1)
switch1.add_if(switch1_for_nic)
nic1_switch1_chan = system.EthChannel(nic1._eth_if, switch1_for_nic)
# connect first switch to second switch
switch0_for_net = system.EthInterface(switch0)
switch0.add_if(switch0_for_net)
switch1_for_net = system.EthInterface(switch1)
switch1.add_if(switch1_for_net)
switch0_switch1_chan = system.EthChannel(switch0_for_net, switch1_for_net)

# configure the software to run on the host
# host0.add_app(system.NetperfClient(host0, nic1._ip))
# host1.add_app(system.NetperfServer(host1))
ping_client_app = system.PingClient(host0, nic1._ip)
ping_client_app.wait = True
host0.add_app(ping_client_app)
host1.add_app(system.Sleep(host1, infinite=True))

"""
Execution Config
"""
for host_type in host_types:
    for nic_type in nic_types:
        for net_type in net_types:
            simulation = sim.Simulation(
                "n-" + host_type + "-" + nic_type + "-" + net_type
            )
            # Host
            if host_type == "gem5":
                host_sim = sim.Gem5Sim
            elif host_type == "qemu":

                def qemu_sim(e):
                    h = sim.QemuSim(e)
                    h.sync = False
                    return h

                host_sim = qemu_sim

            elif host_type == "qt":
                host_sim = sim.QemuSim
            else:
                raise NameError(host_type)

            # NIC
            if nic_type == "i40e":
                nic_sim = sim.I40eNicSim
            elif nic_type == "vr":
                nic_sim = sim.CorundumVerilatorNICSim
            else:
                raise NameError(nic_type)

            # Net
            if net_type == "switch":
                net_sim = sim.SwitchNet
            else:
                raise NameError(net_type)

            host_inst0 = sim.QemuSim(simulation)
            host_inst0.add(host0)
            host_inst0.name = "Client-Host"
            # host_inst0.wait_terminate = True
            # host_inst0.cpu_type = 'X86KvmCPU'

            # host_inst1 = sim.Gem5Sim(simulation)
            host_inst1 = sim.QemuSim(simulation)
            host_inst1.name = "Server-Simulator"
            host_inst1.add(host1)
            # host_inst1.cpu_type = 'X86KvmCPU'

            nic_inst0 = sim.I40eNicSim(simulation=simulation)
            # nic_inst0 = sim.CorundumBMNICSim(simulation)
            # nic_inst0 = sim.CorundumVerilatorNICSim(simulation)
            nic_inst0.add(nic0)

            nic_inst1 = sim.I40eNicSim(simulation=simulation)
            nic_inst1.add(nic1)

            # net_inst = sim.SwitchNet(simulation)
            # net_inst = sim.NS3BridgeNet(simulation=simulation)
            # net_inst.add(switch)

            net_inst = sim.NS3DumbbellNet(simulation=simulation)
            net_inst.add(left=switch0, right=switch1)

            sim_helpers.enable_sync_simulation(
                simulation=simulation, amount=500, ratio=sim.Time.Nanoseconds
            )
            # sim_helpers.disalbe_sync_simulation(simulation=simulation)

            print(simulation.name + "   all simulators:")
            sims = simulation.all_simulators()
            for s in sims:
                print(s)

            experiments.append(simulation)

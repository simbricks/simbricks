from simbricks.components.i40e import system as i40e_sys
from simbricks.components.i40e.simulation import behavioral as i40e_sim
from simbricks.components.ns3.simulation import ns3
from simbricks.components.qemu import simulation as qemu_sim
from simbricks.orchestration import instantiation as inst
from simbricks.orchestration import simulation as sim
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers

"""
Ping ns-3 Example:
One Qemu client: Host0, one Qemu server: Host1 connected through a switch
(One ns-3 client: Host2, one ns-3 server: Host3 connected through a switch)
                ________________________
               |                  ns-3  |
HOST0 -- NIC0 -|-------- SWITCH --------|- NIC1 -- HOST1
               | (HOST2 --|  |-- HOST3) |
               |________________________|
"""

instantiations: list[inst.Instantiation] = []

# ============ SYSTEM ============

sys = system.System()

# create disk images
distro_disk_image = system.DistroDiskImage(sys, "base")

# create a host instance and a NIC instance then install the NIC on the host
host0 = i40e_sys.I40ELinuxHost(sys)
host0.add_disk(distro_disk_image)
host0.add_disk(system.LinuxConfigDiskImage(sys, host0))

nic0 = i40e_sys.IntelI40eNIC(sys)
nic0.add_ipv4("10.0.0.1")
host0.connect_pcie_dev(nic0)

# create a second host instance and a NIC instance
host1 = i40e_sys.I40ELinuxHost(sys)
host1.add_disk(distro_disk_image)
host1.add_disk(system.LinuxConfigDiskImage(sys, host1))

nic1 = i40e_sys.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
host1.connect_pcie_dev(nic1)

# create a host instance simulated in ns-3
# host2 = system.Host(sys)
# host2.parameters["ip"] = "10.0.0.3/24"
# host2_eth_if = system.EthInterface(host2)
# host2.add_if(host2_eth_if)

# create a second host instance simulated in ns-3
# host3 = system.Host(sys)
# host3.parameters["ip"] = "10.0.0.4/24"
# host3_eth_if = system.EthInterface(host3)
# host3.add_if(host3_eth_if)

switch = system.EthSwitch(sys)
# connect switch to NICs
switch_nic0 = system.EthInterface(switch)
switch.add_if(switch_nic0)
switch_nic0_chan = system.EthChannel(nic0._eth_if, switch_nic0)
switch_nic0_chan.latency = "2ms"
switch_nic1 = system.EthInterface(switch)
switch.add_if(switch_nic1)
switch_nic1_chan = system.EthChannel(nic1._eth_if, switch_nic1)
switch_nic1_chan.latency = "2ms"

# # connect switch to ns-3 hosts
# switch_host2 = system.EthInterface(switch)
# switch.add_if(switch_host2)
# switch_host2_chan = system.EthChannel(host2_eth_if, switch_host2)
# switch_host2_chan.latency = "2ms"
# switch_host3 = system.EthInterface(switch)
# switch.add_if(switch_host3)
# switch_host3_chan = system.EthChannel(host3_eth_if, switch_host3)
# switch_host3_chan.latency = "2ms"

# configure the software to run on the host
sleep_app = system.Sleep(host0, infinite=True)
sleep_app.wait = False
host0.add_app(sleep_app)
ping_app = system.PingClient(host1, "10.0.0.1")
ping_app.wait = True
host1.add_app(ping_app)

# ping_app = system.Application(host3)
# ping_app.parameters['type_id'] = 'ns3::Ping'
# ping_app.parameters['start_time'] = '1s'
# ping_app.parameters['stop_time'] = '15s'
# ns3_ping_params = {
#     'Destination(Ipv4Address)': '10.0.0.3',
#     #'Size': '16',
#     'Count': '10',
#     'Timeout': '1s',
#     #'VerboseMode': 'Silent',
# }
# ping_app.parameters['ns3_params'] = ns3_ping_params
# ping_app.wait = True
# host3.add_app(ping_app)

# ============ SIMULATION ============

simulation = sim.Simulation(name="simple-ping-ns3", system=sys)

host_inst0 = qemu_sim.QemuSim(simulation)
host_inst0.add(host0)
host_inst0.name = "Server-Host"

nic_inst0 = i40e_sim.I40eNicSim(simulation=simulation)
nic_inst0.add(nic0)

host_inst1 = qemu_sim.QemuSim(simulation)
host_inst1.add(host1)
host_inst1.name = "Client-Host"

nic_inst1 = i40e_sim.I40eNicSim(simulation=simulation)
nic_inst1.add(nic1)

net_inst = ns3.NS3Net(simulation)
# net_inst.add(host2)
# net_inst.add(host3)
net_inst.add(switch)
# net_inst.use_file = False
net_inst.global_conf.stop_time = "60s"
# net_inst.global_conf.mapping["Progress"] = "100ms,20s"
# net_inst.logging.add_logging("Ping", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("BridgeNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("SimpleNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("SimbricksNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)

# simulation.enable_synchronization()

instance = inst_helpers.simple_instantiation(simulation)
instantiations.append(instance)

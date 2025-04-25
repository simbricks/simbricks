from simbricks.orchestration import system
from simbricks.orchestration import simulation as sim
from simbricks.orchestration.simulation.net import ns3_components
from simbricks.orchestration import instantiation as inst
from simbricks.orchestration.helpers import simulation as sim_helpers

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

# create a host instance and a NIC instance then install the NIC on the host
host0 = system.I40ELinuxHost(sys)
cfg_disk0 = system.DistroDiskImage(h=host0, name="base")
host0.add_disk(cfg_disk0)
tar_disk0 = system.LinuxConfigDiskImage(h=host0)
host0.add_disk(tar_disk0)

pcie0 = system.PCIeHostInterface(host0)
host0.add_if(pcie0)
nic0 = system.IntelI40eNIC(sys)
nic0.add_ipv4("10.0.0.1")
pcichannel0 = system.PCIeChannel(pcie0, nic0._pci_if)

# create a second host instance and a NIC instance
host1 = system.I40ELinuxHost(sys)
cfg_disk1 = system.DistroDiskImage(h=host1, name="base")
host1.add_disk(cfg_disk1)
tar_disk1 = system.LinuxConfigDiskImage(h=host1)
host1.add_disk(tar_disk1)

pcie1 = system.PCIeHostInterface(host1)
host1.add_if(pcie1)
nic1 = system.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
pcichannel1 = system.PCIeChannel(pcie1, nic1._pci_if)

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
switch_nic0_chan.latency = 2 * 10**6 # 2ms
switch_nic1 = system.EthInterface(switch)
switch.add_if(switch_nic1)
switch_nic1_chan = system.EthChannel(nic1._eth_if, switch_nic1)
switch_nic1_chan.latency = 2 * 10**6 # 2ms
# connect switch to ns-3 hosts
# switch_host2 = system.EthInterface(switch)
# switch.add_if(switch_host2)
# switch_host2_chan = system.EthChannel(host2_eth_if, switch_host2)
# switch_host2_chan.latency = 2 * 10**6 # 2ms
# switch_host3 = system.EthInterface(switch)
# switch.add_if(switch_host3)
# switch_host3_chan = system.EthChannel(host3_eth_if, switch_host3)
# switch_host3_chan.latency = 2 * 10**6 # 2ms

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

host_inst0 = sim.QemuSim(simulation)
host_inst0.add(host0)
host_inst0.name = "Server-Host"

nic_inst0 = sim.I40eNicSim(simulation=simulation)
nic_inst0.add(nic0)

host_inst1 = sim.QemuSim(simulation)
host_inst1.add(host1)
host_inst1.name = "Client-Host"

nic_inst1 = sim.I40eNicSim(simulation=simulation)
nic_inst1.add(nic1)

net_inst = sim.NS3Net(simulation)
# net_inst.add(host2)
# net_inst.add(host3)
net_inst.add(switch)
#net_inst.use_file = False
net_inst.global_conf.stop_time = '60s'
# net_inst.global_conf.mapping["Progress"] = "100ms,20s"
# net_inst.logging.add_logging("Ping", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("BridgeNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("SimpleNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)
# net_inst.logging.add_logging("SimbricksNetDevice", ns3_components.NS3LoggingLevel.LEVEL_ALL)

# sim_helpers.enable_sync_simulation(
#     simulation=simulation, amount=500, ratio=sim.Time.Nanoseconds
# )
sim_helpers.disalbe_sync_simulation(simulation=simulation)

print(simulation.name + "   all simulators:")
sims = simulation.all_simulators()
for s in sims:
    print(s)

instance = inst.Instantiation(sim=simulation)
instance.preserve_tmp_folder = False
instance.create_checkpoint = False
#instance.output_artifact_paths = ["simbricks-workdir/output"]

instantiations.append(instance)

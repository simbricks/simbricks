"""
Simple example of a distributed simulation: host0, nic0, and switch are executed in one fragment and
nic1 and host1 in another. We connect the two fragments via a TCP proxy in each fragment, which
allows executing them on separate runners or machines. 
 ___________________________   ________________
|                           | |                |
|  host0 -- nic0 -- switch -|-|- nic1 -- host1 |
|___________________________| |________________|
"""

from simbricks.orchestration import instantiation as inst
from simbricks.orchestration import simulation as sim
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers

sys = system.System()

# create a host instance and a NIC instance then install the NIC on the host
# host0 = system.CorundumLinuxHost(sys)
host0 = system.I40ELinuxHost(sys)
host0.name = "host0"
host0.add_disk(system.DistroDiskImage(h=host0, name="base"))
host0.add_disk(system.LinuxConfigDiskImage(h=host0))

nic0 = system.IntelI40eNIC(sys)
nic0.name = "nic0"
nic0.add_ipv4("10.0.0.1")
host0.connect_pcie_dev(nic0)


# create a host instance and a NIC instance then install the NIC on the host
host1 = system.I40ELinuxHost(sys)
host1.name = "host1"
host1.add_disk(system.DistroDiskImage(h=host1, name="base"))
host1.add_disk(system.LinuxConfigDiskImage(h=host1))

nic1 = system.IntelI40eNIC(sys)
nic1.name = "nic1"
nic1.add_ipv4("10.0.0.2")
host1.connect_pcie_dev(nic1)


switch = system.EthSwitch(sys)
switch.name = "switch"
switch.connect_eth_peer_if(nic0._eth_if)
switch_nic1_channel = switch.connect_eth_peer_if(nic1._eth_if)

# configure the software to run on the host
ping_client_app = system.PingClient(host0, nic1._ip)
ping_client_app.wait = True
host0.add_app(ping_client_app)
host1.add_app(system.Sleep(host1, infinite=True))

# create instantiation
simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: sim.QemuSim,
        system.IntelI40eNIC: sim.I40eNicSim,
        system.EthSwitch: sim.SwitchNet,
    },
)
instantiation = inst_helpers.simple_instantiation(simulation)

# create fragments and specify which types of runners they should execute on
fragment0 = inst.Fragment("SimbricksLocalRunner")
fragment1 = inst.Fragment("SimbricksLocalRunner")
# assign simulators to fragments
fragment0_sims = {simulation.find_sim(comp) for comp in [host0, nic0, switch]}
fragment1_sims = {simulation.find_sim(comp) for comp in [host1, nic1]}
fragment0.add_simulators(*fragment0_sims)
fragment1.add_simulators(*fragment1_sims)
# Assign fragments to instantiation. This also validates that every simulator is assigned to exactly
# one fragment.
instantiation.fragments = [fragment0, fragment1]

# create a pair of proxies and assign it the simulation channel between switch and nic1
proxy_pair = instantiation.create_proxy_pair(inst.TCPProxy, fragment0, fragment1)
proxy_pair.assign_sim_channel(switch_nic1_channel)

# indicate all instantiations that this script provides
instantiation.finalize_validate()  # this is optional to see validation errors early
instantiations = [instantiation]

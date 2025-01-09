from simbricks.orchestration import system
from simbricks.orchestration import simulation as sim
from simbricks.orchestration.helpers import simulation as sim_helpers
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.instantiation import proxy
from simbricks.orchestration.instantiation import fragment
from simbricks.orchestration.instantiation import socket

sys = system.System()

# create a host instance and a NIC instance then install the NIC on the host
# host0 = system.CorundumLinuxHost(sys)
host0 = system.I40ELinuxHost(sys)
host0.add_disk(system.DistroDiskImage(h=host0, name="base"))
host0.add_disk(system.LinuxConfigDiskImage(h=host0))

nic0 = system.IntelI40eNIC(sys)
nic0.add_ipv4("10.0.0.1")
host0.connect_pcie_dev(nic0)


# create a host instance and a NIC instance then install the NIC on the host
host1 = system.I40ELinuxHost(sys)
host1.add_disk(system.DistroDiskImage(h=host1, name="base"))
host1.add_disk(system.LinuxConfigDiskImage(h=host1))

nic1 = system.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
host1.connect_pcie_dev(nic1)


switch0 = system.EthSwitch(sys)
switch0.connect_eth_peer_if(nic0._eth_if)
switch0_nic1_if = system.EthInterface(switch0)
switch0.add_if(switch0_nic1_if)
switch0_nic1_channel = system.EthChannel(switch0_nic1_if, nic1._eth_if)

# configure the software to run on the host
ping_client_app = system.PingClient(host0, nic1._ip)
ping_client_app.wait = True
host0.add_app(ping_client_app)
host1.add_app(system.Sleep(host1, infinite=True))

simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: sim.QemuSim,
        system.IntelI40eNIC: sim.I40eNicSim,
        system.EthSwitch: sim.SwitchNet,
    },
)

instantiation = inst_helpers.simple_instantiation(simulation)
instantiations = [instantiation]

# Create fragments and assign simulators
fragment0 = fragment.Fragment()
fragment0_sims = {simulation.find_sim(comp) for comp in [host0, nic0, switch0]}
fragment0.add_simulators(fragment0_sims)
fragment1 = fragment.Fragment()
fragment1_sims = {simulation.find_sim(comp) for comp in [host1, nic1]}
fragment1.add_simulators(fragment1_sims)

# Create proxies
proxy0 = proxy.TCPProxy()
proxy0.add_interfaces(switch0_nic1_if)
proxy0.connection_mode = socket.SockType.LISTEN
fragment0.add_proxies(proxy0)
proxy1 = proxy.TCPProxy()
proxy1.add_interfaces(nic1._eth_if)
proxy1.connection_mode = socket.SockType.CONNECT
fragment1.add_proxies(proxy1)

instantiation.simulation_fragments = [fragment0, fragment1]

# Define runners
runner0_label = "runner0"
runner1_label = "runner1"

# Map simulation fragments to runners
instantiation.fragment_runner_map = {
    fragment0: runner0_label,
    fragment1: runner1_label,
}

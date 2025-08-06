from simbricks.orchestration import instantiation as inst
from simbricks.orchestration import simulation as sim
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers

sys = system.System()

host0 = system.EnsoHost(sys)
host0.add_disk(system.LinuxConfigDiskImage(sys, host0))
nic0 = system.EnsoBMNIC(sys)
host0.connect_pcie_dev(nic0)

host1 = system.EnsoHost(sys)
host1.add_disk(system.LinuxConfigDiskImage(sys, host1))
nic1 = system.EnsoBMNIC(sys)
host1.connect_pcie_dev(nic1)

switch0 = system.EthSwitch(sys)
switch0.connect_eth_peer_if(nic0._eth_if)
switch0.connect_eth_peer_if(nic1._eth_if)

ensogen_app = system.EnsoGen(host0)
ensogen_app.wait = True
host0.add_app(ensogen_app)

echo_server_app = system.EnsoEchoServer(host1)
host1.add_app(echo_server_app)

simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: sim.QemuSim,
        system.EnsoBMNIC: sim.EnsoNICSim,
        system.EthSwitch: sim.SwitchNet,
    },
)

instantiation = inst_helpers.simple_instantiation(simulation)
fragment = inst.Fragment()
fragment.add_simulators(*simulation.all_simulators())
instantiation.fragments = [fragment]

instantiations = [instantiation]

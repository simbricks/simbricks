from simbricks.components.i40e import system as i40e_sys
from simbricks.components.i40e.simulation import behavioral as i40e_sim
from simbricks.components.net.simulation import base as net_sim
from simbricks.components.qemu import simulation as qemu_sim
from simbricks.orchestration import system
# from simbricks.orchestration.system import nic as sys_nic
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers

sys = system.System()

# create disk images
distro_disk_image = system.DistroDiskImage(sys, "base")

# create a host instance and a NIC instance then install the NIC on the host
host0 = i40e_sys.I40ELinuxHost(sys)
host0.add_disk(distro_disk_image)
host0.add_disk(system.LinuxConfigDiskImage(sys, host0))
# optionally set kernel cli parameter to disable predictable interface naming
# host0.kcmd_append = " net.ifnames=0 biosdevname=0 "

nic0 = i40e_sys.IntelI40eNIC(sys)
# Instead of the I40e NIC, you can also execute a virtio nic as part of a QEMU instance
# nic0 = sys_nic.VirtIONic(sys)
nic0.add_ipv4("10.0.0.1")
host0.connect_pcie_dev(nic0)

# create a host instance and a NIC instance then install the NIC on the host
host1 = i40e_sys.I40ELinuxHost(sys)
host1.add_disk(distro_disk_image)
host1.add_disk(system.LinuxConfigDiskImage(sys, host1))

nic1 = i40e_sys.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
host1.connect_pcie_dev(nic1)


switch0 = system.EthSwitch(sys)
switch0.connect_eth_peer_if(nic0._eth_if)
switch0.connect_eth_peer_if(nic1._eth_if)

# configure the software to run on the host
ping_client_app = system.PingClient(host0, nic1._ip)
ping_client_app.wait = True
host0.add_app(ping_client_app)
host1.add_app(system.Sleep(host1, infinite=True))

simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: qemu_sim.QemuSim,
        i40e_sys.IntelI40eNIC: i40e_sim.I40eNicSim,
        system.EthSwitch: net_sim.SwitchNet,
    },
)

# The VirtIONic must be executed alongside a QEMU instance
# simulation = sim_helpers.simple_simulation(
#     sys,
#     compmap={
#         system.FullSystemHost: qemu_sim.QemuSim,
#         system.EthSwitch: net_sim.SwitchNet,
#     },
# )
# qemu_sim_host_0 = simulation.find_sim(host0)
# qemu_sim_host_0.add(nic0)
# nic1_sim = i40e_sim.I40eNicSim(simulation)
# nic1_sim.add(nic1)

# E.g. in the case of QEMU, you can specify a separate initrd
# qemu_sims = filter(lambda s: isinstance(s, qemu_sim.QemuSim), simulation.all_simulators())
# for qs in qemu_sims:
#     qs: qemu_sim.QemuSim
#     qs.initrd = "global_input/images/base/boot/initrd"

# simulation.enable_synchronization()

instantiation = inst_helpers.simple_instantiation(simulation)

# potentially set input artifacts
# fragment = instantiation.fragments[0]
# fragment.input_artifact_paths = ["experiments/minimal_net.py"]
# instantiation.input_artifact_paths = ["experiments/minimal_net_dist.py"]

# potentially collect output artifacts
# fragment.output_artifact_paths = ["output"]

instantiations = [instantiation]

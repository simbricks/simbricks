"""Two hosts pinging each other, on an image built by this script.

The base image plus a few changes, built on the runner during prepare. Needs the
simbricks-imagebuild-guestfs package there.

    simbricks-run --verbose --global-input-dir <dir> experiments/custom_image.py
"""

from simbricks.components.i40e import system as i40e_sys
from simbricks.components.i40e.simulation import behavioral as i40e_sim
from simbricks.components.net.simulation import base as net_sim
from simbricks.components.qemu import simulation as qemu_sim
from simbricks.imagebuild.guestfs import GuestfsImage
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers

sys = system.System()

base_image = system.DistroDiskImage(sys, "base")

# Layers run in order, offline in one virt-customize invocation: no VM is booted.
image = GuestfsImage(sys, base_image)
image.run("apt-get update && apt-get install -y --no-install-recommends iperf3")
image.add_file("/etc/simbricks-demo.conf", "hello from the orchestration script\n")
# These take files from the submitting machine and ship them to the runner.
# image.copy_in("./mybench", "/usr/local/bin/mybench", mode=0o755)
# image.run_script("./setup-my-software.sh")

hosts, nics = [], []
for index, ip in enumerate(["10.0.0.1", "10.0.0.2"]):
    host = i40e_sys.I40ELinuxHost(sys)
    host.add_disk(image)
    host.add_disk(system.LinuxConfigDiskImage(sys, host))
    nic = i40e_sys.IntelI40eNIC(sys)
    nic.add_ipv4(ip)
    host.connect_pcie_dev(nic)
    hosts.append(host)
    nics.append(nic)

switch = system.EthSwitch(sys)
for nic in nics:
    switch.connect_eth_peer_if(nic._eth_if)

ping = system.PingClient(hosts[0], nics[1]._ip)
ping.wait = True
hosts[0].add_app(ping)
hosts[1].add_app(system.Sleep(hosts[1], infinite=True))

simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: qemu_sim.QemuSim,
        i40e_sys.IntelI40eNIC: i40e_sim.I40eNicSim,
        system.EthSwitch: net_sim.SwitchNet,
    },
)

instantiation = inst_helpers.simple_instantiation(simulation)
instantiations = [instantiation]

# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Two gem5 hosts with i40e NICs on a switch, set up for run streams.

Once the run is going, from another terminal:

  simbricks-cli runs forward <run> -L 7000:tcp:connect:127.0.0.1:7000
  gdb -ex 'target remote 127.0.0.1:7000' <vmlinux>      # gem5's gdb stub for host0

  simbricks-cli runs tail <run> -f output/<gem5 sim dir>/simbricks.log
  simbricks-cli runs tail <run> -f output/pci-writes.<gem5 sim dir>.txt

The gdb stub is on by default; GEM5_VARIANT=opt also turns on SimBricks PCI
debug tracing into simbricks.log in gem5's output directory, which is only
ever read through a stream and never persisted. scripts/log_filter.py is
shipped with the fragment and run next to each gem5 as a ShellProcess; it
reduces the trace to the PCI writes as it grows, and only that summary ends up
in the output artifact.
"""

import os
import pathlib

from simbricks.components.gem5.simulation import gem5 as gem5_sim
from simbricks.components.i40e import system as i40e_sys
from simbricks.components.i40e.simulation import behavioral as i40e_sim
from simbricks.components.net.simulation import base as net_sim
from simbricks.imagebuild.guestfs import GuestfsImage
from simbricks.orchestration import instantiation as inst
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers

variant = os.environ.get("GEM5_VARIANT", "fast")
cpu_type = os.environ.get("GEM5_CPU", "AtomicSimpleCPU")

sys = system.System()

# gem5 boots from a raw image and needs the uncompressed kernel handed to it;
# a layered image provides both, the distro image alone only qcow2.
base_image = system.Ubuntu2204CustomKernelDiskImage(sys)
disk_image = GuestfsImage(sys, base_image)

host0 = i40e_sys.I40ELinuxHost(sys)
host0.add_disk(disk_image)
host0.add_disk(system.LinuxConfigDiskImage(sys, host0))
nic0 = i40e_sys.IntelI40eNIC(sys)
nic0.add_ipv4("10.0.0.1")
host0.connect_pcie_dev(nic0)

host1 = i40e_sys.I40ELinuxHost(sys)
host1.add_disk(disk_image)
host1.add_disk(system.LinuxConfigDiskImage(sys, host1))
nic1 = i40e_sys.IntelI40eNIC(sys)
nic1.add_ipv4("10.0.0.2")
host1.connect_pcie_dev(nic1)

switch0 = system.EthSwitch(sys)
switch0.connect_eth_peer_if(nic0._eth_if)
switch0.connect_eth_peer_if(nic1._eth_if)

ping = system.PingClient(host0, nic1._ip)
ping.wait = True
host0.add_app(ping)
host1.add_app(system.Sleep(host1, infinite=True))

simulation = sim_helpers.simple_simulation(
    sys,
    compmap={
        system.FullSystemHost: gem5_sim.Gem5Sim,
        i40e_sys.IntelI40eNIC: i40e_sim.I40eNicSim,
        system.EthSwitch: net_sim.SwitchNet,
    },
)

for sim in simulation.all_simulators():
    if not isinstance(sim, gem5_sim.Gem5Sim):
        continue
    sim._variant = variant
    sim.cpu_type = cpu_type
    # the gdb stub only comes up when gem5 is told to listen; it picks the first
    # free port from 7000 and says which on stdout
    sim.extra_main_args = ["--listener-mode=on"]
    if variant == "opt":
        sim.extra_main_args += ["--debug-flags=SimBricksPci", "--debug-file=simbricks.log"]

instantiation = inst_helpers.simple_instantiation(simulation)

if variant == "opt":
    # runs next to each gem5 in its fragment, follows the debug trace and keeps the writes
    filter_script = pathlib.Path(__file__).resolve().parent / "scripts" / "log_filter.py"
    fragment = instantiation.fragments[0]
    for sim in simulation.all_simulators():
        if not isinstance(sim, gem5_sim.Gem5Sim):
            continue
        summary = f"pci-writes.{sim.full_name()}-{sim.id()}.txt"
        ready = f"{inst.InstantiationEnvironment.path_placeholder('tmp_simulation_files')}/pci-filter-{sim.id()}.ready"
        filt = inst.ShellProcess(
            f"python3 {inst.ShellProcess.input_file_placeholder(str(filter_script))}"
            f" --log {inst.Instantiation.sim_output_placeholder(sim)}/simbricks.log"
            f" --pattern write"
            f" --out {inst.InstantiationEnvironment.path_placeholder('output_base')}/{summary}"
            f" --ready {ready}",
            input_files=[str(filter_script)],
            name=f"pci-filter-{sim.id()}",
        )
        # ready once the script handles signals: stopping it early then still drains the log
        filt.ready_files.append(ready)
        filt.output_paths.append(f"output/{summary}")
        # AFTER_SIMULATORS (the default): interrupted only once gem5 has exited
        filt.start_after(sim)
        fragment.add_processes(filt)

instantiations = [instantiation]

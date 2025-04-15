# Copyright 2024 Max Planck Institute for Software Systems, and
# National University of Singapore
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

import re
import asyncio
from matplotlib import pyplot as plt
from simbricks.orchestration import system
from simbricks.orchestration import simulation as sim
from simbricks.orchestration import instantiation as inst
from simbricks.utils import base as utils_base
from simbricks.client.opus import base as opus_base

"""
Simple Netperf Example:
One Client: Host_0, One Server: Host1 connected through a switch
HOST0 -- NIC0 ------ SWITCH ------ NIC1 -- HOST1
client                                     server
"""


"""
PARAMETERS TO ADJUST:
nic_sys: The specification of the NIC that shall be simulated. Possible values are 
         e.g. 'CorundumNIC' or 'IntelI40eNIC'.
host_sys: The hosts system confiugration. This choice may also depend on the NIC 
          that is specified for usage to ensure the required drivers are available.
          Possible values are e.g. 'CorundumLinuxHost' or 'I40ELinuxHost'.
nic_sim: The simulator choice for the nic that is specified by the system. Can 
         be e.g. 'CorundumBMNICSim' or 'CorundumVerilatorNICSim'
host_sim: The simulator choice for the hosts. Can be e.g. 'sim.QemuSim' or 'sim.Gem5Sim'.
pci_latency: The pci latency between the hosts and the nics
iperf_udp_rates: A list of transfer rates used by the 'IperfUDPClient' determining the transfer rate.
run_synchronized: Bool flag to enable or disable synchronization for the actual 
                  simulation of the virtual prototype. 
"""
nic_sys = system.IntelI40eNIC
host_sys = system.I40ELinuxHost
nic_sim = sim.I40eNicSim
host_sim = sim.QemuSim
pci_latency = 500  # nanoseconds
run_synchronized = False
iperf_udp_rates = ["150m", "300m"]
client_name = "Sending-Client"


"""
The instantiations list that is used by the SimBricks runtime to create a simulation run of you virtual prototype. 
"""
instantiations: list[inst.Instantiation] = []

for rate in iperf_udp_rates:
    """
    Specify the system you want to simulate
    """
    sys = system.System()

    """
    Create HOST0, the client host in our topology
    """
    host0 = host_sys(sys)
    host0.add_disk(system.DistroDiskImage(h=host0, name="base"))
    host0.add_disk(system.LinuxConfigDiskImage(h=host0))
    """
    Create NIC0, and connect it to HOST0
    """
    nic0 = nic_sys(sys)
    nic0.add_ipv4("10.0.0.1")
    host0.connect_pcie_dev(nic0)

    """
    Create HOST1, the server host in our topology
    """
    host1 = host_sys(sys)
    host1.add_disk(system.DistroDiskImage(h=host1, name="base"))
    host1.add_disk(system.LinuxConfigDiskImage(h=host1))
    """
    Create NIC1, and connect it to HOST1
    """
    nic1 = nic_sys(sys)
    nic1.add_ipv4("10.0.0.2")
    host1.connect_pcie_dev(nic1)

    """
    Create an ethernet switch and connect the NICs from client and server to the switch
    """
    switch = system.EthSwitch(sys)
    switch.connect_eth_peer_if(nic0._eth_if)
    switch.connect_eth_peer_if(nic1._eth_if)

    """
    Specify the software i.e. applciations to run on the hosts, in this case netperf
    """
    client_app = system.IperfUDPClient(h=host0, server_ip=nic1._ip)
    client_app.wait = True
    client_app.rate = rate
    host0.add_app(client_app)

    server_app = system.IperfUDPServer(h=host1)
    host1.add_app(server_app)

    """
    Adjust pci latencies of channels connecting hosts and nics
    """
    sys.latencies(
        amount=pci_latency,
        ratio=utils_base.Time.Nanoseconds,
        channel_type=system.PCIeChannel,
    )

    """
    Specify the simulators to use for your system
    """
    simulation = sim.Simulation(name="My-very-first-test-simulation", system=sys)

    host_inst0 = host_sim(simulation)
    host_inst0.name = client_name
    host_inst0.add(host0)

    host_inst1 = host_sim(simulation)
    host_inst1.add(host1)

    nic_inst0 = nic_sim(simulation=simulation)
    nic_inst0.add(nic0)

    nic_inst1 = nic_sim(simulation=simulation)
    nic_inst1.add(nic1)

    net_inst = sim.SwitchNet(simulation)
    net_inst.add(switch)

    """
    Enable that the experiment shall be run synchronized, i.e. with accurate timing
    """
    if run_synchronized:
        simulation.enable_synchronization(amount=500, ratio=utils_base.Time.Nanoseconds)

    """
    Create an instatiation of your virtual prototype
    """
    instance = inst.Instantiation(sim=simulation)
    fragment = inst.Fragment()
    fragment.add_simulators(*simulation.all_simulators())
    instance.fragments = [fragment]
    instantiations.append(instance)


if __name__ == "__main__":
    """
    Simple method to submit and run aboves instantiations via a python script.
    This is a simple demonsttration of how one could parse immediately parse the
    experiment output to create e.g. a plot.
    """

    async def submit_and_plot():
        averages = []
        run_ids = []
        for instance in instantiations:
            run_ids.append(await opus_base.create_run(instantiation=instance))
        for run_id in run_ids:
            data = []
            line_gen = opus_base.ConsoleLineGenerator(run_id=run_id, follow=True)
            async for _, line in line_gen.generate_lines():
                pattern = r"(\d+\.?\d*)\s*MBytes"
                match = re.search(pattern, line)
                if not match:
                    continue
                m_bytes = float(match.group(1))
                if m_bytes > float(iperf_udp_rates[0].replace("m", "")):
                    continue
                data.append(m_bytes * 8)
            averages.append(sum(data) / len(data))

        plt.bar(iperf_udp_rates, averages)
        plt.title("Parameters Comparison Chart")
        plt.xlabel("Configuration Parameters")
        plt.ylabel("MBytes/sec Transferred")
        plt.savefig("demochart.png")

    asyncio.run(submit_and_plot())

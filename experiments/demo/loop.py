import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from simbricks.orchestration import simulation as sim
from simbricks.orchestration import system
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import simulation as sim_helpers
from helpers import sys_host_nic

"""
Simple example of a simulation: All components are executed in the same fragment.
 _________________________________________________________________________
|                                                                        |
|  Iperf-Server -- Server-NIC -- Switch ----- Client-NIC -- Iperf-CLient |
|________________________________________________________________________|

We define different rates at which the Iperf UDP client tries to send packets 
and create 3 instantiations (one for each rate).
"""

instantiations = []

iperf_rates = ["150m", "430m", "600m"]
for rate in iperf_rates:

    """
    System configuration
    """
    sys = system.System()

    # We create a Linux disk image instance that will be used by the hosts we create.
    # The image used here is provided by SimBricks, user can however also provide custom images.
    distro_disk_image = system.DistroDiskImage(sys, "base")

    # Configure the server to start an Iperf server by adding an application to the server object.
    server_host, server_nic = sys_host_nic(
        sys, distro_disk_image, "10.0.0.1", "Iperf-Server", "Server-NIC"
    )
    server_host.add_app(system.IperfUDPServer(server_host))

    # Configure the client to start an Iperf client by adding an application to the client object.
    # Besides, we set the wait flag on the application to tell SimBricks to run until this application is completed.
    client_host, client_nic = sys_host_nic(
        sys, distro_disk_image, "10.0.0.2", "Iperf-Client", "Client-NIC"
    )
    ping_client_app = system.IperfUDPClient(client_host, server_nic._ip, rate)
    ping_client_app.wait = True
    client_host.add_app(ping_client_app)

    # Create a network switch that connects the server and client NICs with each other.
    switch0 = system.EthSwitch(sys)
    for nic in [server_nic, client_nic]:
        switch0.connect_eth_peer_if(nic._eth_if)

    """
    Simulation configuration
    """

    # We make a simulator choice by simply mapping component types to simulators.
    simulation = sim_helpers.simple_simulation(
        sys,
        compmap={
            system.FullSystemHost: sim.QemuSim,
            system.IntelI40eNIC: sim.I40eNicSim,
            system.EthSwitch: sim.SwitchNet,
        },
    )
    # simulation.enable_synchronization()

    """
    Instantiation configuration
    """

    # Instantiate the virtual prototype
    instantiation = inst_helpers.simple_instantiation(simulation)
    instantiations.append(instantiation)

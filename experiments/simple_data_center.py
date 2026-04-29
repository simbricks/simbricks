import ipaddress
import random
from simbricks.orchestration import system
from simbricks.orchestration import simulation as sim
from simbricks.orchestration.simulation.net import ns3_components
from simbricks.orchestration import instantiation as inst
from simbricks.orchestration.helpers import instantiation as inst_helpers
from simbricks.orchestration.helpers import system as sys_helpers

"""
Simple Data Center Example:

Simulate a topology consisting of one spine switch and N_RACKS many racks. Each rack contains a TOR
switch and a mix of abstractly simulated hosts for background traffic (simulated in ns-3) and hosts
(+ a separate NIC) running a full Linux stack and the desired workload (simulated in QEMU and
dedicated NIC simulator).
"""

N_RACKS = 2
N_DETAILED_HOSTS_PER_RACK = 1
N_NS3_HOSTS_PER_RACK = 3

if N_RACKS * N_DETAILED_HOSTS_PER_RACK % 2 != 0 or N_RACKS * N_NS3_HOSTS_PER_RACK % 2 != 0:
    print("Number of detailed hosts and ns-3 hosts must each be even")
    exit(1)

LINK_LATENCY = 100000 # in nanoseconds
LINK_BANDWIDTH_SPINE = "10Gbps"
LINK_BANDWIDTH_TOR = "1Gbps"

class Host:
    def __init__(self, host: system.Host):
        self.host: system.Host = host
        self.nic: system.SimplePCIeNIC | None = None
        self.channel: system.EthChannel | None = None
        self.ip: str | None = None
        self.ip_prefix: str | None = None

instantiations: list[inst.Instantiation] = []

# ============ SYSTEM ============

sys = system.System()

# IP network for assigning IP addresses to hosts
ip_network = ipaddress.ip_network("10.0.0.0/16")
ips = ip_network.hosts()
ip_prefix = f"/{ip_network.prefixlen}"

# Create spine switch
spine_switch = system.EthSwitch(sys)
spine_switch.name = "Spine Switch"

# Create TOR switches
tor_switches: list[tuple[system.EthSwitch, system.EthChannel]] = []
for i_tor in range(N_RACKS):
    tor_switch = system.EthSwitch(sys)
    tor_switch.name = f"TOR Switch-{i_tor}"
    channel = sys_helpers.connect_eth_devices(spine_switch, tor_switch)
    channel.set_latency(LINK_LATENCY)
    channel.parameters['data_rate'] = LINK_BANDWIDTH_SPINE
    tor_switches.append((tor_switch, channel))

# Create ns-3 hosts and connect them to TOR
ns3_hosts: list[list[Host]] = []
for i_tor_switch in range(N_RACKS):
    rack_hosts = []
    for i_host in range(N_NS3_HOSTS_PER_RACK):
        sys_host = system.Host(sys)
        sys_host.name = f"Ns-3 Host-{i_tor_switch}-{i_host}"
        host = Host(sys_host)

        channel = sys_helpers.connect_eth_devices(tor_switches[i_tor_switch][0], sys_host)
        channel.set_latency(LINK_LATENCY)
        channel.parameters['data_rate'] = LINK_BANDWIDTH_TOR
        host.channel = channel

        host.ip = str(next(ips))
        host.ip_prefix = ip_prefix
        sys_host.parameters["ip"] = host.ip + ip_prefix

        rack_hosts.append(host)
    ns3_hosts.append(rack_hosts)

# Create disk images for hosts running Linux
distro_disk_image = system.DistroDiskImage(sys, "base")

# Create detailed hosts and connect them to TOR
detailed_hosts: list[list[Host]] = []
for i_tor_switch in range(N_RACKS):
    rack_hosts = []
    for i_host in range(N_DETAILED_HOSTS_PER_RACK):
        # create a host instance and a NIC instance then install the NIC on the host
        sys_host = system.I40ELinuxHost(sys)
        sys_host.name = f"Detailed Host-{i_tor_switch}-{i_host}"
        host = Host(sys_host)
        sys_host.add_disk(distro_disk_image)
        sys_host.add_disk(system.LinuxConfigDiskImage(sys, sys_host))

        nic = system.IntelI40eNIC(sys)
        sys_host.connect_pcie_dev(nic)
        host.nic = nic

        channel = tor_switches[i_tor_switch][0].connect_eth_peer_if(nic._eth_if)
        channel.set_latency(LINK_LATENCY)
        channel.parameters['data_rate'] = LINK_BANDWIDTH_TOR
        host.channel = channel

        host.ip = str(next(ips))
        host.ip_prefix = ip_prefix
        nic.add_ipv4(host.ip)

        rack_hosts.append(host)
    detailed_hosts.append(rack_hosts)

# Set applications of ns-3 hosts for background traffic
ns3_pairs = [i for i in range(N_RACKS * N_NS3_HOSTS_PER_RACK)]
random.shuffle(ns3_pairs)
for i in range(N_RACKS * N_NS3_HOSTS_PER_RACK // 2):
    host0_rack_id = ns3_pairs[2*i] // N_NS3_HOSTS_PER_RACK
    host0_host_id = ns3_pairs[2*i] % N_NS3_HOSTS_PER_RACK
    host0 = ns3_hosts[host0_rack_id][host0_host_id]

    packet_sink = system.Application(host0.host)
    packet_sink.parameters["type_id"] = "ns3::PacketSink"
    packet_sink.parameters["ns3_params"] = {
        "Protocol": "ns3::TcpSocketFactory",
        "Local(InetSocketAddress)": host0.ip + ":5001",
    }
    host0.host.add_app(packet_sink)

    host1_rack_id = ns3_pairs[2*i+1] // N_NS3_HOSTS_PER_RACK
    host1_host_id = ns3_pairs[2*i+1] % N_NS3_HOSTS_PER_RACK
    host1 = ns3_hosts[host1_rack_id][host1_host_id]

    on_off_app = system.Application(host1.host)
    on_off_app.parameters["type_id"] = "ns3::OnOffApplication"
    on_off_time = ns3_components.E2ENS3UniformRandomVariable()
    on_off_time.min = 1
    on_off_time.max = 5
    on_off_app.parameters["ns3_params"] = {
        "Protocol": "ns3::TcpSocketFactory",
        "Remote(InetSocketAddress)": host0.ip + ":5001",
        "DataRate": "100Mb/s",
        "OnTime": on_off_time.get_config(),
        "OffTime": on_off_time.get_config(),
    }
    host1.host.add_app(on_off_app)

# Set applications for detailed hosts (Iperf clients and servers)
detailed_pairs = [i for i in range(N_RACKS * N_DETAILED_HOSTS_PER_RACK)]
random.shuffle(detailed_pairs)
for i in range(N_RACKS * N_DETAILED_HOSTS_PER_RACK // 2):
    host0_rack_id = detailed_pairs[2*i] // N_DETAILED_HOSTS_PER_RACK
    host0_host_id = detailed_pairs[2*i] % N_DETAILED_HOSTS_PER_RACK
    host0 = detailed_hosts[host0_rack_id][host0_host_id]
    iperf_server_app = system.IperfTCPServer(host0.host)
    host0.host.add_app(iperf_server_app)

    host1_rack_id = detailed_pairs[2*i+1] // N_DETAILED_HOSTS_PER_RACK
    host1_host_id = detailed_pairs[2*i+1] % N_DETAILED_HOSTS_PER_RACK
    host1 = detailed_hosts[host1_rack_id][host1_host_id]
    iperf_client_app = system.IperfTCPClient(host1.host, host0.ip)
    iperf_client_app.wait = True
    host1.host.add_app(iperf_client_app)

# ============ SIMULATION ============

simulation = sim.Simulation(name="simple-data-center", system=sys)

# Simulate detailed hosts with QEMU and their NICs with an I40e simulator
for i_tor_switch in range(N_RACKS):
    for i_host in range(N_DETAILED_HOSTS_PER_RACK):
        host = detailed_hosts[i_tor_switch][i_host]
        host_inst = sim.QemuSim(simulation)
        host_inst.add(host.host)
        host_inst.name = f"Qemu-Host-{i_tor_switch}-{i_host}"

        nic_inst = sim.I40eNicSim(simulation=simulation)
        nic_inst.add(host.nic)

# Simulate the rest of the system with ns-3
net_inst = sim.NS3Net(simulation)
net_inst.add(spine_switch)
for i_tor_switch in range(N_RACKS):
    net_inst.add(tor_switches[i_tor_switch][0])
    for i_host in range(N_NS3_HOSTS_PER_RACK):
        net_inst.add(ns3_hosts[i_tor_switch][i_host].host)

#simulation.enable_synchronization()

# ============ INSTANTIATION ============

instantiation = inst_helpers.simple_instantiation(simulation)

instantiations.append(instantiation)

from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import nic as sys_nic
from simbricks.orchestration.system.host import base as sys_host_base
from simbricks.orchestration.system.host import app as sys_app_base
from simbricks.orchestration.helpers import system as helpers_sys

from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.simulation import pcidev as sim_pcidev
from simbricks.orchestration.simulation import host as sim_host
from simbricks.orchestration.simulation import net as sim_net
from simbricks.orchestration.simulation import channel as sim_chan
from simbricks.orchestration.helpers import simulation as helpers_sim

# TODO: check and change name
experiments = []


def boilerplate():
    """
    SYSTEM CONFIGURATION
    """
    system = sys_base.System()

    # create client host
    host0 = sys_host_base.CorundumLinuxHost()
    host0_app = sys_app_base.PingClient(host0)
    host0_app.server_ip = "10.0.0.2"
    host0.add_app(host0_app)

    # create client nic
    nic0 = sys_nic.CorundumNIC()
    nic0.add_ipv4("10.0.0.1")

    # connect client host and nic
    host_pci0 = sys_pcie.PCIeHostInterface(host0)
    host0.add_if(host_pci0)
    nic_pci0 = sys_pcie.PCIeDeviceInterface(nic0)
    nic0.add_if(nic_pci0)
    host0_nic0_chan = sys_pcie.PCIeChannel(host_pci0, nic_pci0)

    # create host server
    host1 = sys_host_base.I40ELinuxHost()
    host1_app = sys_app_base.Sleep(host1)
    host1.add_app(host1_app)

    # create host nic
    nic1 = sys_nic.IntelI40eNIC()
    nic1.add_ipv4("10.0.0.2")

    # connect host server to host client
    host_pci1 = sys_pcie.PCIeHostInterface(host0)
    host1.add_if(host_pci1)
    nic_pci1 = sys_pcie.PCIeDeviceInterface(nic1)
    nic1.add_if(nic_pci1)
    host1_nic1_chan = sys_pcie.PCIeChannel(host_pci1, nic_pci1)

    # create first switch
    switch0 = sys_eth.EthSwitch(system)

    # create second switch
    switch1 = sys_eth.EthSwitch(system)

    # connect first switch to client nic
    nic_eth0 = sys_eth.EthInterface(nic0)
    nic0.add_if(nic_eth0)
    switch0_for_nic = sys_eth.EthInterface(switch0)
    switch0.add_if(switch0_for_nic)
    nic0_switch0_chan = sys_eth.EthChannel(nic_eth0, switch0_for_nic)

    # connect second switch to server nic
    nic_eth1 = sys_eth.EthInterface(nic1)
    nic1.add_if(nic_eth1)
    switch1_for_nic = sys_eth.EthInterface(switch1)
    switch1.add_if(switch1_for_nic)
    nic1_switch1_chan = sys_eth.EthChannel(nic_eth1, switch1_for_nic)

    # connect first switch to second switch
    switch0_for_net = sys_eth.EthInterface(switch0)
    switch0.add_if(switch0_for_net)
    switch1_for_net = sys_eth.EthInterface(switch1)
    switch1.add_if(switch1_for_net)
    switch0_switch1_chan = sys_eth.EthChannel(switch0_for_net, switch1_for_net)

    """
    SIMULATION CONFIGURATION
    """
    simulation = sim_base.Simulation("n-" + host_type + "-" + nic_type + "-" + net_type)

    # resolve the host type and simulator
    host_type = ""
    host_sim = None
    match host_type:  # NOTE: synchronized or not is a question of the channel and NOT the simulator anymore!!!!!!!!!
        case "gem5":
            host_sim = sim_host.Gem5Sim
        case "qemu":
            host_sim = sim_host.QemuSim
        case _:
            raise Exception(f"unknown host type {host_type}")
    assert host_sim

    # resolve the nic type and simulator
    nic_type = ""
    nic_sim = None
    match nic_type:  # NOTE: synchronized or not is a question of the channel and NOT the simulator anymore!!!!!!!!!
        case "bm":
            nic_sim = sim_pcidev.CorundumBMNICSim
        case "vr":
            nic_sim = sim_pcidev.CorundumVerilatorNICSim
        case _:
            raise Exception(f"unknown nic type {nic_type}")
    assert nic_sim

    # resolve the network type and simulator
    net_type = ""
    net_sim = None
    match net_type:
        case "bms":
            net_sim = sim_net.SwitchNet
        case "mbms":
            net_sim = sim_net.MemSwitchNet
        case _:
            raise Exception(f"unknown net type {net_type}")
    assert net_type

    host_inst0 = host_sim(simulation)
    host_inst0.add(host0)

    host_inst1 = host_sim(simulation)
    host_inst1.add(host1)

    nic_inst0 = nic_sim(simulation)
    nic_inst0.add(nic0)

    nic_inst1 = nic_sim(simulation)
    nic_inst1.add(nic1)

    switch_inst0 = net_sim(simulation)
    switch_inst0.add(switch0)

    switch_inst1 = net_sim(simulation)
    switch_inst1.add(switch1)

    # enble synchronizaiton
    for chan in simulation.get_all_channels(lazy=False):
        chan._synchronized = True
        chan.set_sync_period(amount=300, ratio=sim_chan.Time.Nanoseconds)

    experiments.append(e)


def syntactic_sugar():
    """
    SYSTEM CONFIGURATION WITH HELPERS
    """
    system = system.System()

    # create client host
    host0 = sys_host_base.CorundumLinuxHost()
    helpers_sys.install_app(
        host=host0, app_ty=sys_app_base.PingClient, server_ip="10.0.0.2"
    )

    # create client nic
    nic0 = sys_nic.CorundumNIC()
    nic0.add_ipv4("10.0.0.1")

    # connect client host and nic
    helpers_sys.connect_host_and_device(host=host0, device=nic0)

    # create host server
    host1 = sys_host_base.I40ELinuxHost()
    helpers_sys.install_app(host=host1, app_ty=sys_app_base.Sleep, delay=10)

    # create host nic
    nic1 = sys_nic.IntelI40eNIC()
    nic1.add_ipv4("10.0.0.2")

    # connect host server to host client
    helpers_sys.connect_host_and_device(host=host1, device=nic1)

    # create first switch
    switch0 = sys_eth.EthSwitch(system)

    # create second switch
    switch1 = sys_eth.EthSwitch(system)

    # connect first switch to client nic
    helpers_sys.connect_eth_devices(device_a=nic0, device_b=switch0)

    # connect second switch to server nic
    helpers_sys.connect_eth_devices(device_a=nic1, device_b=switch1)

    # connect first switch to second switch
    helpers_sys.connect_eth_devices(device_a=switch0, device_b=switch1)

    """
    SIMULATION CONFIGURATION WITH HELPERS
    """

    simulation = sim_base.Simulation("n-" + host_type + "-" + nic_type + "-" + net_type)

    # resolve the host type and simulator
    host_type = ""
    host_sim = None
    match host_type:  # NOTE: synchronized or not is a question of the channel and NOT the simulator anymore!!!!!!!!!
        case "gem5":
            host_sim = sim_host.Gem5Sim
        case "qemu":
            host_sim = sim_host.QemuSim
        case _:
            raise Exception(f"unknown host type {host_type}")
    assert host_sim

    # resolve the nic type and simulator
    nic_type = ""
    nic_sim = None
    match nic_type:  # NOTE: synchronized or not is a question of the channel and NOT the simulator anymore!!!!!!!!!
        case "bm":
            nic_sim = sim_pcidev.CorundumBMNICSim
        case "vr":
            nic_sim = sim_pcidev.CorundumVerilatorNICSim
        case _:
            raise Exception(f"unknown nic type {nic_type}")
    assert nic_sim

    # resolve the network type and simulator
    net_type = ""
    net_sim = None
    match net_type:
        case "bms":
            net_sim = sim_net.SwitchNet
        case "mbms":
            net_sim = sim_net.MemSwitchNet
        case _:
            raise Exception(f"unknown net type {net_type}")
    assert net_type

    host_inst0 = host_sim(simulation)
    # helper to add multiple specifications in single func call
    helpers_sim.add_specs(host_inst0, host0)

    host_inst1 = host_sim(simulation)
    host_inst1.add(host1)

    nic_inst0 = nic_sim(simulation)
    nic_inst0.add(nic0)

    nic_inst1 = nic_sim(simulation)
    nic_inst1.add(nic1)

    switch_inst0 = net_sim(simulation)
    switch_inst0.add(switch0)

    switch_inst1 = net_sim(simulation)
    switch_inst1.add(switch1)

    # enble synchronizaiton
    helpers_sim.enable_sync_simulation(
        simulation=simulation, amount=300, ratio=sim_chan.Time.Nanoseconds
    )
    # helpers_sim.disalbe_sync_simulation(simulation=simulation)

    experiments.append(e)

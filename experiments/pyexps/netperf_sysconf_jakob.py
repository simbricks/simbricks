from simbricks.orchestration.system import base as sys_base
from simbricks.orchestration.system import pcie as sys_pcie
from simbricks.orchestration.system import eth as sys_eth
from simbricks.orchestration.system import nic as sys_nic
from simbricks.orchestration.system.host import base as sys_host_base
from simbricks.orchestration.system.host import app as sys_app_base
from simbricks.orchestration.helpers import system as helpers_sys


def boilerplate():
    """
    SYSTEM CONFIGURATION
    """
    system = sys_base.System()

    # create client host
    host0 = sys_host_base.CorundumLinuxHost()
    host0_app = sys_app_base.PingClient(host0)
    host0.add_app(host0_app)

    # create client nic
    nic0 = sys_nic.CorundumNIC()
    nic0.set_ipv4("10.0.0.1")

    # connect client host and nic
    host_pci0 = sys_pcie.PCIeHostInterface(host0)
    host0.add_if(host_pci0)
    nic_pci0 = sys_pcie.PCIeDeviceInterface(nic0)
    nic0.set_pcie_if(nic_pci0)
    host0_nic0_chan = sys_pcie.PCIeChannel(host_pci0, nic_pci0)

    # create host server
    host1 = sys_host_base.I40ELinuxHost()
    host1_app = sys_app_base.Sleep(host1)
    host1.add_app(host1_app)

    # create host nic
    nic1 = sys_nic.IntelI40eNIC()
    nic1.set_ipv4("10.0.0.2")

    # connect host server to host client
    host_pci1 = sys_pcie.PCIeHostInterface(host0)
    host1.add_if(host_pci1)
    nic_pci1 = sys_pcie.PCIeDeviceInterface(nic1)
    nic1.set_pcie_if(nic_pci1)
    host1_nic1_chan = sys_pcie.PCIeChannel(host_pci1, nic_pci1)

    # create first switch
    switch0 = sys_eth.EthSwitch(system)

    # create second switch
    switch1 = sys_eth.EthSwitch(system)

    # connect first switch to client nic
    nic_eth0 = sys_eth.EthInterface(nic0)
    nic0.set_eth_if(nic_eth0)
    switch0_for_nic = sys_eth.EthInterface(switch0)
    switch0.if_add(switch0_for_nic)
    nic0_switch0_chan = sys_eth.EthChannel(nic_eth0, switch0_for_nic)

    # connect second switch to server nic
    nic_eth1 = sys_eth.EthInterface(nic1)
    nic1.set_eth_if(nic_eth1)
    switch1_for_nic = sys_eth.EthInterface(switch1)
    switch1.if_add(switch1_for_nic)
    nic1_switch1_chan = sys_eth.EthChannel(nic_eth1, switch1_for_nic)

    # connect first switch to second switch
    switch0_for_net = sys_eth.EthInterface(switch0)
    switch0.if_add(switch0_for_net)
    switch1_for_net = sys_eth.EthInterface(switch1)
    switch1.if_add(switch1_for_net)
    switch0_switch1_chan = sys_eth.EthChannel(switch0_for_net, switch1_for_net)

    """
    SIMULATION CONFIGURATION
    """


def syntactic_sugar():
    """
    SYSTEM CONFIGURATION SYNTACTIC SUGAR
    """
    system = system.System()

    # create client host
    host0 = sys_host_base.CorundumLinuxHost()
    install_application(host0, sys_app_base.PingClient(host0))

    # create client nic
    nic0 = sys_nic.CorundumNIC()
    nic0.add_ipv4("10.0.0.1")

    # connect client host and nic
    helpers_sys.connect_host_and_device(host=host0, device=nic0)

    # create host server
    host1 = sys_host_base.I40ELinuxHost()
    install_application(host1, system.Sleep(host1))

    # create host nic
    nic1 = sys_nic.IntelI40eNIC()
    nic1.set_ipv4("10.0.0.2")

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

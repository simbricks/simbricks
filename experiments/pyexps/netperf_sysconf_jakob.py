
from simbricks.orchestration import system  

"""
SYSTEM CONFIGURATION
"""
def boilerplate():
    system = system.System()

    # create client host
    host0 = system.CorundumLinuxHost()
    host0_app = system.PingClient(host0) 
    host0.add_app(host0_app)

    # create client nic
    nic0 = system.CorundumNIC()
    nic0.set_ipv4('10.0.0.1')

    # connect client host and nic
    host_pci0 = system.PCIeHostInterface(host0)
    host0.add_if(host_pci0)
    nic_pci0 = system.PCIeDeviceInterface(nic0)
    nic0.set_pcie_if(nic_pci0)
    host0_nic0_chan = system.PCIeChannel(host_pci0, nic_pci0)
    
    # create host server
    host1 = system.I40ELinuxHost()
    host1_app = system.Sleep(host1) 
    host1.add_app(host1_app)

    # create host nic
    nic1 = system.I40eNIC()
    nic1.set_ipv4('10.0.0.2')

    # connect host server to host client
    host_pci1 = system.PCIeHostInterface(host0)
    host1.add_if(host_pci1)
    nic_pci1 = system.PCIeDeviceInterface(nic1)
    nic1.set_pcie_if(nic_pci1)
    host1_nic1_chan = system.PCIeChannel(host_pci1, nic_pci1)

    # create first switch
    switch0 = system.EthSwitch(system)

    # create second switch
    switch1 = system.EthSwitch(system)

    # connect first switch to client nic
    nic_eth0 = system.EthInterface(nic0)
    nic0.set_eth_if(nic_eth0)
    switch0_for_nic = system.EthInterface(switch0)
    switch0.if_add(switch0_for_nic)
    nic0_switch0_chan = system.EthChannel(nic_eth0, switch0_for_nic)

    # connect second switch to server nic
    nic_eth1 = system.EthInterface(nic1)
    nic1.set_eth_if(nic_eth1)
    switch1_for_nic = system.EthInterface(switch1)
    switch1.if_add(switch1_for_nic)
    nic1_switch1_chan = system.EthChannel(nic_eth1, switch1_for_nic)

    # connect first switch to second switch
    switch0_for_net = system.EthInterface(switch0)
    switch0.if_add(switch0_for_net)
    switch1_for_net = system.EthInterface(switch1)
    switch1.if_add(switch1_for_net)
    switch0_switch1_chan = system.EthChannel(switch0_for_net, switch1_for_net)


"""
SYSTEM CONFIGURATION SYNTACTIC SUGAR
"""
def syntactic_sugar():
    system = system.System()

    # create client host
    host0 = system.CorundumLinuxHost()
    install_application(host0, system.PingClient(host0))

    # create client nic
    nic0 = system.CorundumNIC()
    nic0.set_ipv4('10.0.0.1')

    # connect client host and nic
    connect_host_and_device(host0, nic0)
    
    # create host server
    host1 = system.I40ELinuxHost()
    install_application(host1, system.Sleep(host1))

    # create host nic
    nic1 = system.I40eNIC()
    nic1.set_ipv4('10.0.0.2')

    # connect host server to host client
    connect_host_and_device(host1, nic1)

    # create first switch
    switch0 = system.EthSwitch(system)

    # create second switch
    switch1 = system.EthSwitch(system)

    # connect first switch to client nic
    connect_net_devices(nic0, switch0)

    # connect second switch to server nic
    connect_net_devices(nic1, switch1)

    # connect first switch to second switch
    connect_net_devices(switch0, switch1)
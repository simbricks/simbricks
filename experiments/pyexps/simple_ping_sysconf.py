import simbricks.splitsim.specification as spec

"""
Simple Ping Example:
Host 0 pings Host1

HOST0 -- NIC0 ------ SWITCH ------ NIC1 -- HOST1

"""
system = spec.System()

# create a host instance and a NIC instance then install the NIC on the host
host0 = spec.Host(system)
nic0 = spec.i40eNIC(system)
host0.nic_driver = 'i40e'
host0.ip = '10.0.0.1'
pcichannel0 = spec.PCI(system)
pcichannel0.install(host0, nic0)

host1 = spec.Host(system)
nic1 = spec.i40eNIC(system)
host1.nic_driver = 'i40e'
host1.ip = '10.0.0.2'
pcichannel1 = spec.PCI(system)
pcichannel1.install(host1, nic1)

port0 = spec.NetDev()
port1 = spec.NetDev()
switch = spec.Switch(system)
switch.install_netdev(port0)
switch.install_netdev(port1)

ethchannel0 = spec.Eth(system)
ethchannel0.install(nic0, port0)
ethchannel1 = spec.Eth(system)
ethchannel1.install(nic1, port1)

# configure the software to run on the host
host0.app = spec.PingClient('10.0.0.2')
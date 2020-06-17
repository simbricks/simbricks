Code structure:
 - `proto/`: protocol definitions for PCIe and Ethernet channels
 - `nicsim_common/`: helper library for NIC simulations
 - `corundum/`: verilator-based cycle accurate Corundum model
 - `corundum_bm/`: C++ behavioral model for Corundum
 - `netsim_common/`: helper library for network simulations
 - `net_tap/`: Linux tap interface connector for Ethernet channel
 - `net_wire/`: Ethernet wire, connects to Ethernet channels together:w

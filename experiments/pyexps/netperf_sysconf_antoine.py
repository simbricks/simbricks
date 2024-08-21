import simbricks.orchestration as cfg
import simbricks.configuration.system as sysc
import simbricks.configuration.utils as utils

def mk_sys():
  system = sysc.System()

  # create a host instance and a NIC instance then install the NIC on the host
  host0 = sysc.CorundumLinuxHost(system)
  pcie0 = sysc.PCIeIf(system)
  host0.if_add(pcie0)
  nic0 = sysc.CorundumNIC(system)
  nic0.add_ipv4('10.0.0.1')
  pcichannel0 = sysc.PCIeChannel(system)
  pcichannel0.install(pcie0, nic0.pcie_if)

  host1 = sysc.CorundumLinuxHost(system)
  pcie1 = sysc.PCIeIf(system)
  host1.if_add(pcie1)
  nic1 = sysc.CorundumNIC(system)
  nic1.add_ipv4('10.0.0.2')
  pcichannel1 = sysc.PCIeChannnel(system)
  pcichannel1.install(pcie1, nic1.pcie_if)

  switch = sysc.Switch(system)
  netif0 = sysc.EthIf(system)
  switch.if_add(netif0)
  netif1 = sysc.EthIf(system)
  switch.if_add(netif1)

  ethchannel0 = sysc.EthChannel(system)
  ethchannel0.install(nic0.eth_if, netif0)
  ethchannel1 = sysc.EthChannel(system)
  ethchannel1.install(nic1.eth_if, netif1)

  # configure the software to run on the host
  host0.app = sysc.NetperfClient(nic0.ipv4_addresses[0])
  host1.app = sysc.NetperfServer()
  return system


def mk_sys_sugared():
  system = sysc.System()

  # create a host instance and a NIC instance then install the NIC on the host
  host0 = sysc.CorundumLinuxHost(system)
  nic0 = sysc.CorundumNIC(system)
  host0.connect_pcie_dev(nic0)

  host1 = sysc.CorundumLinuxHost(system)
  nic1 = sysc.CorundumNIC(system)
  host1.connect_pcie_dev(nic2)

  utils.net.allocate_ipv4(system)

  switch = sysc.Switch(system)
  switch.connect_eth_dev(nic0)
  switch.connect_eth_dev(nic1)

  # configure the software to run on the host
  host0.app = sysc.NetperfClient(nic0.ipv4_addresses[0])
  host1.app = sysc.NetperfServer()
  return system


import simbricks.configuration.impl as implc

def instantiate_simple

"""
Execution Config
"""
for host_type in host_types:
    for nic_type in nic_types:
        for net_type in net_types:
            e = exp.Experiment(
                'n-' + host_type + '-' + nic_type + '-' + net_type
            )
            allobj = runobj.AllObj()

            # Host
            if host_type == 'gem5':
                host_sim = impl.Gem5Sim
            elif host_type == 'qemu':

                def qemu_sim(e):
                    h = impl.QemuSim(e)
                    h.sync = False
                    return h
                host_sim = qemu_sim

            elif host_type == 'qt':
                host_sim = impl.QemuSim
            else:
                raise NameError(host_type)
            
            # NIC
            if nic_type == 'bm':
                nic_sim = impl.CorundumBMNICSim
            elif nic_type == 'vr':
                nic_sim = impl.CorundumVerilatorNICSim
            else:
                raise NameError(nic_type)

            # Net
            if net_type == 'switch':
                net_sim = impl.SwitchBMSim
            else:
                raise NameError(net_type)


            host_inst0 = host_sim(e, allobj)
            host_inst0.add(host0)

            host_inst1 = host_sim(e, allobj)
            host_inst1.add(host1)

            nic_inst0 = nic_sim(e, allobj)
            nic_inst0.add(nic0)

            nic_inst1 = nic_sim(e, allobj)
            nic_inst1.add(nic1)

            net_inst = net_sim(e, allobj)
            net_inst.add(switch)
            
            print(e.name + "   all simulators:")
            sims = e.all_simulators()
            for sim in sims:
                print(sim)

            experiments.append(e)
# Copyright 2021 Max Planck Institute for Software Systems, and
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
"""Validation experiment for our PCI interface by running with the builtin gem5
e1000 NIC, and then with the extracted gem5 e1000 NIC connected through
SimBricks."""

import simbricks.nodeconfig as node
import simbricks.simulators as sim

import simbricks.experiments as exp

experiments = []

for internal in [True, False]:
    if internal:
        e = exp.Experiment('pci_validation-internal')
    else:
        e = exp.Experiment('pci_validation-external')
    e.checkpoint = False

    net = sim.SwitchNet()
    e.add_network(net)

    server = sim.Gem5Host()
    server.name = 'server'
    nc_server = node.E1000LinuxNode()
    nc_server.prefix = 24
    nc_server.ip = '10.0.0.1'
    nc_server.force_mac_addr = '00:90:00:00:00:01'
    nc_server.app = node.NetperfServer()
    server.set_config(nc_server)
    e.add_host(server)

    client = sim.Gem5Host()
    client.name = 'client'
    nc_client = node.E1000LinuxNode()
    nc_client.prefix = 24
    nc_client.ip = '10.0.0.2'
    nc_client.force_mac_addr = '00:90:00:00:00:02'
    nc_client.app = node.NetperfClient()
    nc_client.app.server_ip = '10.0.0.1'
    nc_client.app.duration_tp = -1000000
    nc_client.app.duration_lat = -1000
    client.set_config(nc_client)
    client.wait = True
    e.add_host(client)

    for h in [client, server]:
        h.cpu_type = h.cpu_type_cp = 'TimingSimpleCPU'
        h.variant = 'opt'  # need opt gem5 variant with debug support
        h.extra_main_args.append(
            '--debug-flags=SimBricksEthernet,SimBricksPci,EthernetAll,EthernetDesc'
        )
        if internal:
            h.add_netdirect(net)
        else:
            nic = sim.E1000NIC()
            nic.debug = True
            nic.set_network(net)
            # force same mac address in HW as in gem5 (same default for both)
            nic.mac = '00:90:00:00:00:01'
            h.add_nic(nic)
            e.add_nic(nic)

    experiments.append(e)

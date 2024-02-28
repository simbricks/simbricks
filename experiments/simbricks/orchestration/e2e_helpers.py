# Copyright 2023 Max Planck Institute for Software Systems, and
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

# Allow own class to be used as type for a method's argument
from __future__ import annotations

import typing as tp
from enum import Enum

import simbricks.orchestration.e2e_components as e2e
from simbricks.orchestration.simulators import NS3E2ENet


class E2ELinkType(Enum):
    SIMBRICKS = 0
    NS3_SIMPLE_CHANNEL = 1


class E2ELinkAssigner():

    def __init__(self):
        self.links = {}
        self.connected_switches = set()
        self.switch_links = {}

    def add_link(
        self,
        idd: str,
        left_switch: e2e.E2ETopologyNode,
        right_switch: e2e.E2ETopologyNode,
        link_type: tp.Optional[E2ELinkType] = None,
        create_link: bool = True
    ):
        if create_link and link_type is None:
            raise RuntimeError("Cannot create a link without link type")
        if idd in self.links:
            raise RuntimeError(f"Link {idd} already exists")
        link = {
            "left": left_switch,
            "right": right_switch,
            "type": link_type,
            "created": create_link
        }
        if create_link:
            self._create_link(idd, link)
        self.links[idd] = link
        self.connected_switches.add(left_switch)
        self.connected_switches.add(right_switch)
        if left_switch in self.switch_links:
            self.switch_links[left_switch].append(link)
        else:
            self.switch_links[left_switch] = [link]
        if right_switch in self.switch_links:
            self.switch_links[right_switch].append(link)
        else:
            self.switch_links[right_switch] = [link]

    # TODO: set properties like latency
    def _create_link(self, idd: str, link):
        left_switch = link["left"]
        right_switch = link["right"]
        link_type = link["type"]
        if link_type == E2ELinkType.SIMBRICKS:
            left_adapter = e2e.E2ENetworkSimbricks(f"_{idd}_left_adapter")
            left_adapter.listen = False
            left_switch.add_component(left_adapter)
            link["left_adapter"] = left_adapter
            right_adapter = e2e.E2ENetworkSimbricks(
                f"_{idd}_right_adapter"
            )
            right_adapter.listen = True
            right_switch.add_component(right_adapter)
            link["right_adapter"] = right_adapter
        elif link_type == E2ELinkType.NS3_SIMPLE_CHANNEL:
            ns3link = e2e.E2ESimpleChannel(f"_{idd}_link")
            ns3link.left_node = left_switch
            ns3link.right_node = right_switch
            link["ns3link"] = ns3link

    def set_link_type(self, idd: str, link_type: E2ELinkType):
        if idd not in self.links:
            raise RuntimeError(f"Link {idd} not found")
        link = self.links[idd]
        if link["created"]:
            raise RuntimeError("Cannot change type of already existing link")
        link["type"] = link_type

    def create_missing_links(self):
        for idd, link in self.links.items():
            if link["created"]:
                continue
            if link["type"] is None:
                raise RuntimeError(f"Link {idd} has no type")
            self._create_link(idd, link)
            link["created"] = True

    def assign_networks(self) -> tp.List[NS3E2ENet]:
        networks = []
        # walk over all connected switches
        while len(self.connected_switches) > 0:
            # create network and take next (random) switch
            net = NS3E2ENet()
            net.name = f"_network_{len(networks)}"
            networks.append(net)
            next_switches = set()
            next_switches.add(self.connected_switches.pop())
            # visit (transitively) all switches that are connected through ns3
            # links and add them to the same network
            while len(next_switches) > 0:
                switch = next_switches.pop()
                net.add_component(switch)
                for link in self.switch_links[switch]:
                    if link["type"] == E2ELinkType.SIMBRICKS:
                        if link["left"] == switch:
                            link["right_adapter"].simbricks_component = net
                        else:
                            assert link["right"] == switch
                            link["left_adapter"].simbricks_component = net
                    elif link["type"] == E2ELinkType.NS3_SIMPLE_CHANNEL:
                        not_visited_switches = 0
                        if link["left"] in self.connected_switches:
                            next_switches.add(link["left"])
                            self.connected_switches.remove(link["left"])
                            not_visited_switches += 1
                        if link["right"] in self.connected_switches:
                            next_switches.add(link["right"])
                            self.connected_switches.remove(link["right"])
                            not_visited_switches += 1
                        assert not_visited_switches < 2
                        # if only one switch has been visited (namely the
                        # current switch), we see this link for the first time
                        if not_visited_switches == 1:
                            net.add_component(link["ns3link"])
                    else:
                        raise RuntimeError("Unknown link type")

        return networks

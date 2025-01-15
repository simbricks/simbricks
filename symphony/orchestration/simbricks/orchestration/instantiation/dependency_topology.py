# Copyright 2025 Max Planck Institute for Software Systems, and
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
"""Module for building instantiation topology for resolving dependencies between
instantiated components like simulators that determines the order to start them
in."""
from __future__ import annotations

import typing
import enum

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base
    from simbricks.orchestration.instantiation import socket as inst_socket
    from simbricks.orchestration.instantiation import proxy as inst_proxy

    class TopologyComponentType(enum.Enum):
        SIMULATOR = enum.auto()
        PROXY = enum.auto()


class TopologyComponent:

    def __init__(
        self,
        type: TopologyComponentType,
        value: sim_base.Simulator | inst_proxy.Proxy,
    ) -> None:
        self.type = type
        self.value = value


SimulationDependencyTopology = typing.NewType(
    "SimulationDependencyTopology",
    dict[TopologyComponent, set[TopologyComponent]],
)
"""Dict mapping from to-be-instantiated component like a simulator to its
dependencies. Dependencies have to start first before component stored as key
can start."""


def build_simulation_topology(
    instantiation: inst_base.Instantiation,
) -> SimulationDependencyTopology:
    # mapping from simulator to its dependencies, i.e., dependencies have to
    # start first before simulator can start
    sim_dependencies: SimulationDependencyTopology = {}

    def insert_dependency(topo_comp_a: TopologyComponent, depends_on: TopologyComponent):
        if depends_on in sim_dependencies:
            if topo_comp_a in sim_dependencies[depends_on]:
                # TODO: FIXME
                raise Exception("detected cylic dependency, this is currently not supported")

        a_dependencies = set()
        if topo_comp_a in sim_dependencies:
            a_dependencies = sim_dependencies[topo_comp_a]

        a_dependencies.add(depends_on)
        sim_dependencies[topo_comp_a] = a_dependencies

    def update_a_depends_on_b(
        inf_a: sys_base.Interface,
        topo_comp_a: TopologyComponent,
        inf_b: sys_base.Interface,
        topo_comp_b: TopologyComponent,
    ) -> None:
        a_sock = topo_comp_a.value.supported_socket_types(interface=inf_a)
        b_sock = topo_comp_a.value.supported_socket_types(interface=inf_b)

        if a_sock != b_sock:
            if len(a_sock) == 0 or len(b_sock) == 0:
                raise Exception(
                    "cannot create socket and resolve dependency if no socket"
                    " type is supported for an interface"
                )
            if inst_socket.SockType.CONNECT in a_sock:
                assert inst_socket.SockType.LISTEN in b_sock
                insert_dependency(topo_comp_a, depends_on=topo_comp_b)
                instantiation._update_get_socket(
                    interface=inf_a, socket_type=inst_socket.SockType.CONNECT
                )
                instantiation._update_get_socket(
                    interface=inf_b, socket_type=inst_socket.SockType.LISTEN
                )
            else:
                assert inst_socket.SockType.CONNECT in b_sock
                insert_dependency(topo_comp_b, depends_on=topo_comp_a)
                instantiation._update_get_socket(
                    interface=inf_b, socket_type=inst_socket.SockType.CONNECT
                )
                instantiation._update_get_socket(
                    interface=inf_a, socket_type=inst_socket.SockType.LISTEN
                )
        else:
            # deadlock?
            if len(a_sock) != 2 or len(b_sock) != 2:
                raise Exception("cannot solve deadlock")
            # both support both we just pick an order
            insert_dependency(topo_comp_a, depends_on=topo_comp_b)
            instantiation._update_get_socket(
                interface=topo_comp_a, socket_type=inst_socket.SockType.CONNECT
            )
            instantiation._update_get_socket(
                interface=topo_comp_b, socket_type=inst_socket.SockType.LISTEN
            )

    # build dependency graph
    for sim in instantiation.fragment.all_simulators():
        for comp in sim.components():
            for sim_inf in comp.interfaces():
                if instantiation._opposing_interface_within_same_sim(interface=sim_inf):
                    # both interfaces of channel are located in the same
                    # simulator
                    continue

                topo_comp_a = TopologyComponent(
                    TopologyComponentType.SIMULATOR, sim
                )
                opposing_inf = instantiation._get_opposing_interface(interface=sim_inf)

                if not instantiation.fragment.interface_handled_by_proxy(opposing_inf):
                    topo_comp_b = TopologyComponent(
                        TopologyComponentType.SIMULATOR,
                        instantiation.find_sim_by_interface(opposing_inf),
                    )
                else:
                    topo_comp_b = TopologyComponent(
                        TopologyComponentType.PROXY,
                        instantiation.fragment.get_proxy_by_interface(opposing_inf),
                    )

                update_a_depends_on_b(sim_inf, topo_comp_a, opposing_inf, topo_comp_b)

    return sim_dependencies

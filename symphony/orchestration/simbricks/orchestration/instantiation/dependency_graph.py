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
"""Module for building graph for determinining starting order of components like simulators and
proxies that runner starts."""
from __future__ import annotations

import enum
import typing

from simbricks.orchestration.instantiation import proxy as inst_proxy
from simbricks.orchestration.instantiation import socket as inst_socket
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.helpers import exceptions as exc

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.system import base as sys_base


class SimulationDependencyNodeType(enum.Enum):
    SIMULATOR = "simulator"
    """Simulator in assigned fragment."""
    PROXY = "proxy"
    """Proxy in assigned fragment."""
    EXTERNAL_PROXY = "external proxy"
    """Proxy outside assigned fragment."""


class SimulationDependencyNode:

    def __init__(
        self,
        type: SimulationDependencyNodeType,
        value: sim_base.Simulator | inst_proxy.Proxy,
    ) -> None:
        self.type = type
        self.value = value

    def get_simulator(self) -> sim_base.Simulator:
        if self.type == SimulationDependencyNodeType.SIMULATOR:
            return typing.cast(sim_base.Simulator, self.value)
        raise RuntimeError("Value stored is not a simulator")

    def get_proxy(self) -> inst_proxy.Proxy:
        if (
            self.type == SimulationDependencyNodeType.PROXY
            or self.type == SimulationDependencyNodeType.EXTERNAL_PROXY
        ):
            return typing.cast(inst_proxy.Proxy, self.value)
        raise RuntimeError("Value stored is not a proxy")

    def __repr__(self) -> str:
        match self.type:
            case SimulationDependencyNodeType.SIMULATOR:
                return str(("sim", self.get_simulator()))
            case SimulationDependencyNodeType.PROXY:
                return str(("proxy", self.get_proxy()))
            case SimulationDependencyNodeType.EXTERNAL_PROXY:
                return str(("external_proxy", self.get_proxy()))
            case _:
                raise RuntimeError("Unhandled type")


SimulationDependencyGraph = typing.NewType(
    "SimulationDependencyGraph",
    dict[SimulationDependencyNode, set[SimulationDependencyNode]],
)
"""Dict mapping from to-be-instantiated component like a simulator to its
dependencies. Dependencies have to start first before the component stored as key can start. All
keys are components from the assigned fragment. Mapped values can also contain components from other
fragments though."""


def _insert_dependency(
    dep_graph: SimulationDependencyGraph,
    node: SimulationDependencyNode,
    depends_on: SimulationDependencyNode,
) -> None:
    """Add `depends_on` as dependency to `node` in graph."""
    if depends_on in dep_graph and node in dep_graph[depends_on]:
        raise Exception("detected cylic dependency, this is currently not supported")

    a_dependencies = set()
    if node in dep_graph:
        a_dependencies = dep_graph[node]
    a_dependencies.add(depends_on)
    dep_graph[node] = a_dependencies


def _insert_dep_if_a_depends_on_b(
    dep_graph: SimulationDependencyGraph,
    inst: inst_base.Instantiation,
    inf_a: sys_base.Interface,
    node_a: SimulationDependencyNode,
    inf_b: sys_base.Interface,
    node_b: SimulationDependencyNode,
):
    """Add a `node_b` as dependency to `node_b` in graph if `node_b` actually needs to start before
    `node_a`. To determine this, the sockets assigned to the given respective interfaces are
    examined."""

    socktype_a = inst.get_interface_socktype(inf_a)
    socktype_b = inst.get_interface_socktype(inf_b)

    if socktype_a == inst_socket.SockType.LISTEN and socktype_b == inst_socket.SockType.CONNECT:
        # Do nothing since b depends on a but not a on b
        pass
    elif socktype_a == inst_socket.SockType.CONNECT and socktype_b == inst_socket.SockType.LISTEN:
        _insert_dependency(dep_graph, node_a, node_b)
    else:
        raise exc.InstantiationConfigurationError(
            f"Invalid socket type assignment for connection between {node_a} and {node_b} with {socktype_a} and {socktype_b}, respectively."
        )


def build_simulation_dependency_graph(
    inst: inst_base.Instantiation,
) -> SimulationDependencyGraph:
    """
    Build a dependency graph for the simulator and proxy starting order. The listening side of a
    SimBricks connection has to be started first since it creates the SHM queue.
    """
    # the actual dependency graph
    dep_graph: SimulationDependencyGraph = SimulationDependencyGraph({})
    # lookup dicts from components that should be started to their corresponding graph nodes
    nodes_sim: dict[sim_base.Simulator, SimulationDependencyNode] = {}
    nodes_proxy: dict[inst_proxy.Proxy, SimulationDependencyNode] = {}

    # add simulator-simulator dependencies for simulators in assigned fragment
    for sim_a in inst.assigned_fragment.all_simulators():
        for comp_a in sim_a.components():
            for inf_a in comp_a.interfaces():
                # both interfaces of channel are located in the same simulator => no dependency
                if inst._opposing_interface_within_same_sim(interface=inf_a):
                    continue

                # get info on other side of channel
                inf_b = inf_a.get_opposing_interface()
                sim_b = inst.find_sim_by_interface(inf_b)

                # other simulator is not part of current fragment, will handle this case later via
                # simulator-proxy dependencies
                if sim_b not in inst.assigned_fragment.all_simulators():
                    if sim_a not in nodes_sim:
                        nodes_sim[sim_a] = (
                            SimulationDependencyNode(SimulationDependencyNodeType.SIMULATOR, sim_a)
                        )
                    continue

                # get / create nodes
                node_a = nodes_sim.setdefault(
                    sim_a,
                    SimulationDependencyNode(SimulationDependencyNodeType.SIMULATOR, sim_a),
                )
                node_b = nodes_sim.setdefault(
                    sim_b,
                    SimulationDependencyNode(SimulationDependencyNodeType.SIMULATOR, sim_b),
                )
                _insert_dep_if_a_depends_on_b(dep_graph, inst, inf_a, node_a, inf_b, node_b)
                _insert_dep_if_a_depends_on_b(dep_graph, inst, inf_b, node_b, inf_a, node_a)

    # optimization: remove proxies that we do not need
    inst.assigned_fragment._remove_unnecessary_proxies(inst)

    # add proxy-simulator dependencies
    for proxy_a in inst.assigned_fragment.all_proxies():
        for inf_a in proxy_a.interfaces:
            # get simulator on other side that proxy is connecting to
            inf_b = inf_a.get_opposing_interface()
            sim_a = inst.find_sim_by_interface(inf_a)

            # simulator node was already created during phase 1
            node_a = nodes_sim[sim_a]

            # create node for proxy
            node_b = nodes_proxy.setdefault(
                proxy_a,
                SimulationDependencyNode(SimulationDependencyNodeType.PROXY, proxy_a),
            )

            _insert_dep_if_a_depends_on_b(dep_graph, inst, inf_a, node_a, inf_b, node_b)
            _insert_dep_if_a_depends_on_b(dep_graph, inst, inf_b, node_b, inf_a, node_a)

    # add proxy-proxy dependencies, i.e. listening proxies create the proxy-proxy connection and
    # therefore have to be started before connecting proxies
    for proxy_a in inst.assigned_fragment.all_proxies():
        node_a = nodes_proxy[proxy_a]  # was added with proxy-simulator dependencies
        proxy_b = inst._find_opposing_proxy(proxy_a)
        assert (
            proxy_b not in inst.assigned_fragment.all_proxies()
        ), "connection between proxies in the same fragment should have been optimized out earlier"
        node_b = nodes_proxy.setdefault(
            proxy_b,
            SimulationDependencyNode(SimulationDependencyNodeType.EXTERNAL_PROXY, proxy_b),
        )

        # Implicit property: proxy_b is located in external fragment. Hence, we only need to add a
        # dependency for proxy_a if it is marked as connecting
        if proxy_a._connection_mode == inst_socket.SockType.CONNECT:
            _insert_dependency(dep_graph, node_a, node_b)

    return dep_graph

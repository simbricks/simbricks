# Copyright 2024 Max Planck Institute for Software Systems, and
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
from __future__ import annotations

import functools
import typing
import uuid

from simbricks.orchestration.instantiation import proxy
from simbricks.utils import base as utils_base

if typing.TYPE_CHECKING:
    from simbricks.orchestration.instantiation import base as inst_base
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.orchestration.system import base as sys_base


class Fragment(utils_base.IdObj):

    def __init__(
        self, fragment_executor_tag: str | None = None, runner_tags: set[str] | None = None
    ):
        super().__init__()

        self._fragment_executor_tag = fragment_executor_tag
        self._runner_tags = set() if runner_tags is None else runner_tags
        """Only execute this fragment on runner that has all given labels."""
        self._proxies: set[proxy.Proxy] = set()
        self._simulators: set[sim_base.Simulator] = set()
        self._parameters: dict[typing.Any, typing.Any] = {}

        self.input_artifact_name: str = f"input-artifact-{str(uuid.uuid4())}.zip"
        self.input_artifact_paths: list[str] = []

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        proxy_json = []
        for prox in self._proxies:
            utils_base.has_attribute(prox, "toJSON")
            proxy_json.append(prox.toJSON())
        json_obj["proxies"] = proxy_json

        json_obj["fragment_executor_tag"] = self._fragment_executor_tag
        json_obj["runner_tags"] = list(self._runner_tags)
        json_obj["simulators"] = list(map(lambda sim: sim.id(), self._simulators))
        json_obj["parameters"] = utils_base.dict_to_json(self._parameters)
        json_obj["cores_required"] = self.cores_required
        json_obj["memory_required"] = self.memory_required

        json_obj["input_artifact_name"] = self.input_artifact_name
        json_obj["input_artifact_paths"] = self.input_artifact_paths

        return json_obj

    @classmethod
    def fromJSON(cls, json_obj: dict, simulation: sim_base.Simulation) -> Fragment:
        instance = super().fromJSON(json_obj)

        instance._fragment_executor_tag = utils_base.get_json_attr_top(
            json_obj, "fragment_executor_tag"
        )
        instance._runner_tags = set(utils_base.get_json_attr_top(json_obj, "runner_tags"))

        proxies_json = utils_base.get_json_attr_top(json_obj, "proxies")
        instance._proxies = set()
        for proxy_json in proxies_json:
            proxy_class = utils_base.get_cls_by_json(proxy_json)
            utils_base.has_attribute(proxy_class, "fromJSON")
            prox = proxy_class.fromJSON(proxy_json, simulation)
            instance._proxies.add(prox)

        simulator_ids = utils_base.get_json_attr_top(json_obj, "simulators")
        instance._simulators = set()
        for simulator_id in simulator_ids:
            simulator = simulation.get_simulator(simulator_id)
            instance._simulators.add(simulator)

        instance._parameters = utils_base.json_to_dict(
            utils_base.get_json_attr_top(json_obj, "parameters")
        )

        instance.input_artifact_name = utils_base.get_json_attr_top(json_obj, "input_artifact_name")
        instance.input_artifact_paths = utils_base.get_json_attr_top(json_obj, "input_artifact_paths")

        return instance

    @property
    def cores_required(self) -> int:
        req_cores_per_sim = map(lambda sim: sim.resreq_cores(), self._simulators)
        req_cores = functools.reduce(lambda x, y: x + y, req_cores_per_sim)
        return req_cores

    @property
    def memory_required(self) -> int:
        req_mem_per_sim = map(lambda sim: sim.resreq_mem(), self._simulators)
        req_mem = functools.reduce(lambda x, y: x + y, req_mem_per_sim)
        return req_mem

    @staticmethod
    def merged(*fragments: Fragment) -> Fragment:
        def compare_labels(a: Fragment, b: Fragment) -> bool:
            if len(a._runner_tags) != len(b._runner_tags):
                return False
            for label in a._runner_tags:
                if label not in b._runner_tags:
                    return False
            return True

        if not fragments:
            raise RuntimeError("cannot merge 0 fragments")
        for fragment in fragments:
            if (fragment._fragment_executor_tag != fragments[0]._fragment_executor_tag
                or not compare_labels(fragment, fragments[0])
            ):
                raise RuntimeError("cannot merge fragments with different fragment executor tags "
                                   "or different runner tags")
        merged_fragment = Fragment(fragments[0]._fragment_executor_tag, fragments[0]._runner_tags)
        proxies = set()
        simulators = set()
        for fragment in fragments:
            proxies.update(fragment.all_proxies())
            simulators.update(fragment.all_simulators())
        merged_fragment._proxies = proxies
        merged_fragment._simulators = simulators
        return merged_fragment

    def add_simulators(self, *sims: sim_base.Simulator):
        self._simulators.update(sims)

    def add_proxies(self, *proxies: proxy.Proxy):
        self._proxies.update(proxies)

    def all_simulators(self) -> set[sim_base.Simulator]:
        return self._simulators

    def all_proxies(self) -> set[proxy.Proxy]:
        return self._proxies

    def find_proxy_by_interface(self, interface: sys_base.Interface) -> proxy.Proxy | None:
        for proxy in self._proxies:
            if interface in proxy._interfaces:
                return proxy
        return None

    def get_proxy_by_interface(self, interface: sys_base.Interface) -> proxy.Proxy:
        """Same as `find_proxy_by_interface()` but raises an Error if interface
        is not assigned to any proxy in this fragment."""
        proxy = self.find_proxy_by_interface(interface)
        if proxy is None:
            raise RuntimeError("Interface not assigned to any proxies in this fragment.")
        return proxy

    def get_proxy_by_id(self, id: int) -> proxy.Proxy:
        # TODO: avoid iterating over all proxies?
        for prox in self._proxies:
            if prox.id() == id:
                return prox
        # TODO: use more specific exception
        raise RuntimeError(f"there is no proxy with id {id}")

    def interface_handled_by_proxy(self, interface: sys_base.Interface) -> bool:
        return self.find_proxy_by_interface(interface) is not None

    def _remove_unnecessary_proxies(self, inst: inst_base.Instantiation) -> None:
        """Remove proxies that connect within this fragment."""
        new_proxies = self._proxies.copy()
        for p in self._proxies:
            if isinstance(p, proxy.DummyProxy):
                new_proxies.remove(p)
            opp_proxy = inst._find_opposing_proxy(p)
            if opp_proxy in self._proxies:
                # opposing proxy is also in the current fragment
                new_proxies.remove(p)
        self._proxies = new_proxies

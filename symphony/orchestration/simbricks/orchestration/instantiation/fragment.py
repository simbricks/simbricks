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

import typing
import functools
from simbricks.utils import base as util_base
from simbricks.orchestration.instantiation import proxy
from simbricks.utils import base as util_base

if typing.TYPE_CHECKING:
    from simbricks.orchestration.simulation import base as sim_base
    from simbricks.orchestration.system import base as sys_base


class Fragment(util_base.IdObj):

    def __init__(self):
        super().__init__()

        self._proxies: set[proxy.Proxy] = set()
        self._simulators: set[sim_base.Simulator] = set()

    def toJSON(self) -> dict:
        json_obj = super().toJSON()

        proxy_json = []
        for prox in self._proxies:
            util_base.has_attribute(prox, "toJSON")
            proxy_json.append(prox.toJSON())
        json_obj["proxies"] = proxy_json

        json_obj["simulators"] = list(map(lambda sim: sim.id(), self._simulators))
        json_obj["cores_required"] = self.cores_required
        json_obj["memory_required"] = self.memory_required
        return json_obj

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

    @classmethod
    def fromJSON(cls, json_obj: dict) -> Fragment:
        instance = super().fromJSON(json_obj)
        # TODO: FIXME implement proper reconstruction from json
        return instance

    @staticmethod
    def merged(*fragments: Fragment):
        merged_fragment = Fragment()
        proxies = set()
        simulators = set()
        for fragment in fragments:
            proxies.update(fragment.all_proxies())
            simulators.update(fragment.all_simulators())
        merged_fragment._proxies = proxies
        merged_fragment._simulators = simulators

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
            if interface in proxy.interfaces:
                return proxy
        return None

    def get_proxy_by_interface(self, interface: sys_base.Interface) -> proxy.Proxy:
        """Same as `find_proxy_by_interface()` but raises an Error if interface
        is assigned to any proxy in this fragment."""
        proxy = self.find_proxy_by_interface(interface)
        if proxy is None:
            raise RuntimeError("Interface not assigned to any proxies in this fragment.")
        return proxy

    def interface_handled_by_proxy(self, interface: sys_base.Interface) -> bool:
        return self.find_proxy_by_interface(interface) is not None

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

import abc
import sys
from 
from simbricks.orchestration import experiments
from simbricks.orchestration.simulation import base
from simbricks.orchestration.system import eth
from simbricks.orchestration.instantiation import base as inst_base


class NetSim(base.Simulator):
    """Base class for network simulators."""

    def __init__(self, e: exp.Experiment) -> None:
        super().__init__(e)
        # TODO: do we want them here?
        self._switch_specs = []
        self._host_specs = []

    def full_name(self) -> str:
        return "net." + self.name

    def dependencies(self) -> list[base.Simulator]:
        # TODO
        deps = []
        for s in self.switches:
            for n in s.netdevs:
                deps.append(n.net[0].sim)
        return deps

    # TODO
    def sockets_cleanup(self, env: exp_env.ExpEnv) -> list[str]:
        pass
    
    # TODO
    def sockets_wait(self, env: exp_env.ExpEnv) -> list[str]:
        pass

    def wait_terminate(self) -> bool:
        # TODO
        return self.wait

    def init_network(self) -> None:
        pass

    def sockets_cleanup(self, env: exp_env.ExpEnv) -> list[str]:
        # TODO
        return []


class SwitchNet(NetSim):

    def __init__(self, e: exp.Experiment) -> None:
        super().__init__(e)
        # TODO: probably we want to store these in a common base class...
        self._switch_spec: eth.EthSwitch | None = None

    def add_switch(self, switch_spec: eth.EthSwitch):
        assert self._switch_spec is None
        super()._add_component(switch_spec)
        self._switch_spec = switch_spec
        self.experimente.add_spec_sim_map(self._switch_spec, self)

    def run_cmd(self, inst: inst_base.Instantiation) -> str:
        assert self._switch_spec is not None

        eth_latency = self._switch_spec.channels()[0].latency
        if any(lat != eth_latency for chan in self._switch_spec.channels()):
            raise Exception("SwitchNet currently only supports single eth latency")

        sync_period = None
        run_sync = False
        sockets: list[inst_base.Socket] = []
        for chan in self._switch_spec.channels():
            channel, socket = self._get_sock_path(inst=inst, chan=chan)
            if channel is None or socket is None:
                continue            
            
            sync_period = min(sync_period, channel.sync_period)
            run_sync = run_sync or channel._synchronized
            sock_paths.append(socket)

        assert sync_period is not None
        assert eth_latency is not None

        cmd = env.repodir + "/sims/net/switch/net_switch"
        cmd += f" -S {sync_period} -E {eth_latency}"

        if not run_sync:
            cmd += " -u"

        if len(env.pcap_file) > 0:
            cmd += " -p " + env.pcap_file

        connect = ''
        listen = ''
        for sock in sockets:
            if sock._type == inst_base.SockType.LISTEN:
                listen += " -h " + sock._path
            else:
                connect += " -s " + sock._path

        cmd += connect
        cmd += listen

        return cmd

    # TODO
    def sockets_cleanup(self, env: exp_env.ExpEnv) -> list[str]:
        # cleanup here will just have listening eth sockets, switch also creates
        # shm regions for each with a "-shm" suffix
        cleanup = []
        for s in super().sockets_cleanup(env):
            cleanup.append(s)
            cleanup.append(s + "-shm")
        return cleanup

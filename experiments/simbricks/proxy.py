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

from simbricks.simulators import Simulator

class SimProxy(Simulator):
    name = ''
    # set by the experiment runner
    ip = ''
    listen = False

    def full_name(self):
        return 'proxy.' + self.name

class NetProxy(SimProxy):
    """ Proxy for connections between NICs and networks. """
    # List of tuples (nic, with_listener)
    nics = None

class NetProxyListener(NetProxy):
    def __init__(self):
        self.listen = True
        self.nics = []
        super().__init__()

    def add_nic(self, nic):
        self.nics.append((nic, True))

class NetProxyConnecter(NetProxy):
    listener = None

    def __init__(self, listener):
        self.listener = listener
        self.nics = listener.nics
        super().__init__()

    def add_nic(self, nic):
        self.nics.append((nic, False))

class RDMANetProxyListener(NetProxyListener):
    port = 12345

    def __init__(self):
        self.listen = True
        super().__init__()

    def run_cmd(self, env):
        cmd = (f'{env.repodir}/dist/net_rdma -l '
            f'-s {env.proxy_shm_path(self)} ')
        for (nic, local) in self.nics:
            cmd += '-d ' if local else '-n '
            cmd += env.nic_eth_path(nic) + ' '
        cmd += f' 0.0.0.0 {self.port}'
        return cmd

class RDMANetProxyConnecter(NetProxyConnecter):
    def __init__(self, listener):
        super().__init__(listener)

    def run_cmd(self, env):
        cmd = (f'{env.repodir}/dist/net_rdma '
            f'-s {env.proxy_shm_path(self)} ')
        for (nic, local) in self.nics:
            cmd += '-n ' if local else '-d '
            cmd += env.nic_eth_path(nic) + ' '
        cmd += f' {self.listener.ip} {self.listener.port}'
        return cmd
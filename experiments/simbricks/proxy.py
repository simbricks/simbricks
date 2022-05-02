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

    def __init__(self):
        super().__init__()

    def full_name(self):
        return 'proxy.' + self.name

class NetProxy(SimProxy):
    """ Proxy for connections between NICs and networks. """
    # List of tuples (nic, with_listener)
    nics = None

    # List of tuples ((netL,netC), with_listener)
    n2ns = None

    # Shared memory size in GB
    shm_size = 2048

    def __init__(self):
        super().__init__()

    def start_delay(self):
        return 10

class NetProxyListener(NetProxy):
    port = 12345
    connecter = None
    listen = True

    def __init__(self):
        super().__init__()
        self.listen = True
        self.nics = []
        self.n2ns = []

    def add_nic(self, nic):
        self.nics.append((nic, True))

        # the network this nic connects to now also depends on the peer
        nic.network.extra_deps.append(self.connecter)

    # add net2net connection with listening network on the listener side
    def add_n2n(self, net_c, net_l):
        self.n2ns.append(((net_c, net_l), True))

        # the connecting network depends on our peer
        net_c.extra_deps.append(self.connecter)

    def dependencies(self):
        deps = []
        for (nic, local) in self.nics:
            if local:
                deps.append(nic)
        for ((net_c, net_l), local) in self.n2ns:
            if local:
                deps.append(net_l)
        return deps

    def sockets_cleanup(self, env):
        socks = []
        for (nic, local) in self.nics:
            if not local:
                socks.append(env.nic_eth_path(nic))
        for ((net_c, net_l), local) in self.n2ns:
            if not local:
                socks.append(env.n2n_eth_path(net_l, net_c))
        return []

    # sockets to wait for indicating the simulator is ready
    def sockets_wait(self, env):
        socks = []
        for (nic, local) in self.nics:
            if not local:
                socks.append(env.nic_eth_path(nic))
        for ((net_c, net_l), local) in self.n2ns:
            if not local:
                socks.append(env.n2n_eth_path(net_l, net_c))
        return socks

    def run_cmd_base(self, env):
        cmd = (f'-s {env.proxy_shm_path(self)} '
            f'-S {self.shm_size} ')
        for (nic, local) in self.nics:
            cmd += '-C ' if local else '-L '
            cmd += env.nic_eth_path(nic) + ' '

        for ((net_c, net_l), local) in self.n2ns:
            cmd += '-C ' if local else '-L '
            cmd += env.n2n_eth_path(net_l, net_c) + ' '

        cmd += f' 0.0.0.0 {self.port}'
        return cmd

class NetProxyConnecter(NetProxy):
    listener = None

    def __init__(self, listener):
        super().__init__()
        self.listener = listener
        listener.connecter = self
        self.nics = listener.nics
        self.n2ns = listener.n2ns

    def add_nic(self, nic):
        self.nics.append((nic, False))

        # the network this nic connects to now also depends on the proxy
        nic.network.extra_deps.append(self.listener)

    # add net2net connection with listening network on the connection side
    def add_n2n(self, net_c, net_l):
        self.n2ns.append(((net_c, net_l), False))
        # the connecting network depends on our peer
        net_c.extra_deps.append(self.listener)

    def dependencies(self):
        deps = [self.listener]
        for (nic, local) in self.nics:
            if not local:
                deps.append(nic)
        for ((net_c, net_l), local) in self.n2ns:
            if not local:
                deps.append(net_l)
        return deps

    def sockets_cleanup(self, env):
        socks = []
        for (nic, local) in self.nics:
            if local:
                socks.append(env.nic_eth_path(nic))
        for ((net_c, net_l), local) in self.n2ns:
            if local:
                socks.append(env.n2n_eth_path(net_l, net_c))
        return []

    # sockets to wait for indicating the simulator is ready
    def sockets_wait(self, env):
        socks = []
        for (nic, local) in self.nics:
            if local:
                socks.append(env.nic_eth_path(nic))
        for ((net_c, net_l), local) in self.n2ns:
            if local:
                socks.append(env.n2n_eth_path(net_l, net_c))
        return socks

    def run_cmd_base(self, env):
        cmd = (f'-s {env.proxy_shm_path(self)} '
            f'-S {self.shm_size} ')
        for (nic, local) in self.nics:
            cmd += '-L ' if local else '-C '
            cmd += env.nic_eth_path(nic) + ' '

        for ((net_c, net_l), local) in self.n2ns:
            cmd += '-L ' if local else '-C '
            cmd += env.n2n_eth_path(net_l, net_c) + ' '

        cmd += f' {self.listener.ip} {self.listener.port}'
        return cmd


class RDMANetProxyListener(NetProxyListener):
    def __init__(self):
        super().__init__()

    def run_cmd(self, env):
        cmd = f'{env.repodir}/dist/rdma/net_rdma -l '
        cmd += super().run_cmd_base(env)
        return cmd

class RDMANetProxyConnecter(NetProxyConnecter):
    def __init__(self, listener):
        super().__init__(listener)

    def run_cmd(self, env):
        cmd = f'{env.repodir}/dist/rdma/net_rdma '
        cmd += super().run_cmd_base(env)
        return cmd


class SocketsNetProxyListener(NetProxyListener):
    def __init__(self):
        super().__init__()

    def run_cmd(self, env):
        cmd = f'{env.repodir}/dist/sockets/net_sockets -l '
        cmd += super().run_cmd_base(env)
        return cmd

class SocketsNetProxyConnecter(NetProxyConnecter):
    def __init__(self, listener):
        super().__init__(listener)

    def run_cmd(self, env):
        cmd = f'{env.repodir}/dist/sockets/net_sockets '
        cmd += super().run_cmd_base(env)
        return cmd
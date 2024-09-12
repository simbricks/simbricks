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

import typing as tp
import io
from os import path
from simbricks.orchestration.experiment import experiment_environment as expenv
from simbricks.orchestration.system import base as base
if tp.TYPE_CHECKING:
    from simbricks.orchestration.system import (eth, mem, pcie)
    from simbricks.orchestration.system.host import disk_images
    from simbricks.orchestration.system.host import app


class Host(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.ifs: list[base.Interface] = []
        self.applications: list['Application']

    def interfaces(self) -> list[base.Interface]:
        return self.pcie_ifs + self.eth_ifs + self.mem_ifs

    def add_if(self, interface: base.Interface) -> None:
        self.ifs.append(i)

    def add_app(self, a: 'Application') -> None:
        self.applications.append(a)


class FullSystemHost(Host):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.memory = 512
        self.cores = 1
        self.cpu_freq = '3GHz'
        self.disks: list['DiskImage'] = []

    def add_disk(self, disk: 'DiskImage') -> None:
        self.disks.append(disk)


class BaseLinuxHost(FullSystemHost):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.applications: list['BaseLinuxApplication'] = []
        self.load_modules = []
        self.kcmd_append = ''

    def add_app(self, a: 'BaseLinuxApplication') -> None:
        self.applications.append(a)

    def _concat_app_cmds(
            self,
            env: expenv.ExpEnv,
            mapper: tp.Callable[['BaseLinuxApplication', expenv.ExpEnv],
                                list[str]]
            ) -> list[str]:
        """
        Generate command list from applications by applying `mapper` to each
        application on this host and concatenating the commands.
        """
        cmds = []
        for app in self.applications:
            cmds += mapper(app, env)
        return cmds

    def run_cmds(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run on node."""
        return self._concat_app_cmds(env, app.LinuxApplication.run_cmds)

    def cleanup_cmds(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to cleanup node."""
        return self._concat_app_cmds(env, app.LinuxApplication.cleanup_cmds)

    def config_files(self, env: expenv.ExpEnv) -> dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        cfg_files = {}
        for app in self.applications:
            cfg_files |= self.app.config_files(env)
        return cfg_files

    def prepare_pre_cp(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        self._concat_app_cmds(env, app.LinuxApplication.prepare_pre_cp)

    def prepare_post_cp(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to prepare node after checkpoint restore."""
        return self._concat_app_cmds(env, app.LinuxApplication.prepare_post_cp)

    def _config_str(self, env: expenv.ExpEnv) -> str:
        if env.create_cp:
            sim = env.exp.get_simulator(self)
            cp_cmd = self.checkpoint_commands()
        else:
            cp_cmd = []

        es = self.prepare_pre_cp(env) + self.app.prepare_pre_cp(env) + \
            cp_cmd + \
            self.prepare_post_cp(env) + self.app.prepare_post_cp(env) + \
            self.run_cmds() + self.cleanup_cmds()
        return '\n'.join(es)

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))


class LinuxHost(BaseLinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers: list[str] = []
    
    def cleanup_cmds(self, env: expenv.ExpEnv) -> list[str]:
        return super().cleanup_cmds(env) + ['poweroff -f']

    def prepare_pre_cp(self, env: expenv.ExpEnv) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        return [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:' + \
                '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"'
        ] + super().prepare_pre_cp(env)

    def prepare_post_cp(self) -> tp.List[str]:
        l = []
        for d in self.drivers:
            if d[0] == '/':
                l.append(f'insmod {d}')
            else:
                l.append(f'modprobe {d}')
        eth_i = 0
        for i in self.interfaces():
            # Get ifname parameter if set, otherwise default to ethX
            if 'ifname' in i.parameters:
                ifn = i.parameters['ifname']
            elif isinstance(i, eth.EthSimpleNIC):
                ifn = f'eth{eth_i}'
                eth_i += 1
            else:
                continue

            # Force MAC if requested
            if 'force_mac_addr' in i.parameters:
                mac = i.parameters['force_mac_addr']
                l.append(f'ip link set dev {ifn} address '
                         f'{mac}')

            # Bring interface up
            l.append(f'ip link set dev {ifn} up')

            # Add IP addresses if included
            if 'ipv4_addrs' in i.parameters:
                for a in i.parameters['ipv4_addrs']:
                    l.append(f'ip addr add {a} dev {ifn}')
        return super().prepare_post_cp() + l


class I40ELinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append('i40e')


class CorundumLinuxHost(LinuxHost):
    def __init__(self, sys) -> None:
        super().__init__(sys)
        self.drivers.append('/tmp/guest/mqnic.ko')

    def config_files(self, env: expenv.ExpEnv) -> tp.Dict[str, tp.IO]:
        m = {'mqnic.ko': open('../images/mqnic/mqnic.ko', 'rb')}
        return {**m, **super().config_files()}
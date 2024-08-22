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
from abc import (ABC)
import os.path

import simbricks.orchestration.system.base as base
import simbricks.orchestration.system.eth as eth
import simbricks.orchestration.system.mem as mem
import simbricks.orchestration.system.pcie as pcie
from simbricks.orchestration.system.host.disk_images import *
from simbricks.orchestration.system.host.app import *


class Host(base.Component):
    def __init__(self, s: base.System):
        super().__init__(s)
        self.ifs: tp.List[pcie.PCIeHostInterface] = []
        self.applications: tp.List[Application]

    def interfaces(self) -> tp.List[base.Interface]:
        return self.pcie_ifs + self.eth_ifs + self.mem_ifs

    def add_if(self, i: base.Interface) -> None:
        self.ifs.append(i)

    def add_app(self, a: Application) -> None:
        self.applications.append(a)


class FullSystemHost(Host):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.memory = 512
        self.cores = 1
        self.cpu_freq = '3GHz'
        self.disks: tp.List[DiskImage] = []

    def add_disk(self, disk: DiskImage) -> None:
        self.disks.append(disk)


class LinuxHost(FullSystemHost):
    def __init__(self, s: base.System) -> None:
        super().__init__(s)
        self.applications: tp.List[LinuxApplication] = []
        self.load_modules = []
        self.kcmd_append = ''

    def add_app(self, a: LinuxApplication) -> None:
        self.applications.append(a)

    def run_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run on node."""
        return self.app.run_cmds(self)

    def cleanup_cmds(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to cleanup node."""
        return []

    def config_files(self, env: expenv.ExpEnv) -> tp.Dict[str, tp.IO]:
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

    def prepare_pre_cp(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to prepare node before checkpointing."""
        return [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:' + \
                '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"'
        ]

    def prepare_post_cp(self, env: expenv.ExpEnv) -> tp.List[str]:
        """Commands to run to prepare node after checkpoint restore."""
        return []

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding='UTF-8'))
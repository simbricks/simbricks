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
import io
import os.path
import tarfile
import typing as tp
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.orchestration.experiment import experiment_environment as expenv
if tp.TYPE_CHECKING:
    from simbricks.orchestration.system.host import base


class DiskImage(abc.ABC):
    def __init__(self, h: 'Host') -> None:
        self.host = None | str

    @abc.abstractmethod
    def available_formats(self) -> list[str]:
        return []

    @abc.abstractmethod
    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        return

    async def prepare_format(self, inst: inst_base.Instantiation, format: str) -> str:
        pass

    async def prepare(self, inst: inst_base.Instantiation) -> None:
        # Find first supported disk image format in order of simulator pref.
        sim = inst.simulation.find_sim(self.host)
        format = None
        av_fmt = self.available_formats()
        for f in sim.supported_image_formats():
            if f in av_fmt:
                format = f
                break

        if format is None:
            raise Exception('No supported image format found')

        await self.prepare_format(inst, format)


# Disk image where user just provides a path
class ExternalDiskImage(DiskImage):
    def __init__(self, h: 'FullSystemHost', path: str) -> None:
        super().__init__(h)
        self.path = path
        self.formats = ["raw", "qcow2"]

    def available_formats(self) -> list[str]:
        return self.formats

    def path(self, inst: inst_base.Instantiation, format: str)  -> str:
        assert os.path.isfile(self.path)
        return self.path


# Disk images shipped with simbricks
class DistroDiskImage(DiskImage):
    def __init__(self, h: 'FullSystemHost', name: str) -> None:
        super().__init__(h)
        self.name = name
        self.formats = ["raw", "qcow2"]

    def available_formats(self) -> list[str]:
        return self.formats

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        path = inst.hd_path(self.name)
        if format == "raw":
            path += ".raw"
        elif format == "qcow":
            pass
        else:
            raise RuntimeError("Unsupported disk format")
        assert os.path.isfile(self.path)
        return self.path

# Abstract base class for dynamically generated images
class DynamicDiskImage(DiskImage):
    def __init__(self, h: 'FullSystemHost', path: str) -> None:
        super().__init__(h)

    def path(self, inst: inst_base.Instantiation, format: str) -> str:
        return inst.dynamic_img_path(self, format)

    @abc.abstractmethod
    async def prepare_format(self, inst: inst_base.Instantiation, format: str) -> str:
        pass

# Builds the Tar with the commands to run etc.
class LinuxConfigDiskImage(DynamicDiskImage):
    def __init__(self, h: 'LinuxHost') -> None:
        super().__init__(h)
        self.host: base.LinuxHost

    def available_formats(self) -> list[str]:
        return ["raw"]

    async def prepare_format(self, inst: inst_base.Instantiation, format: str) -> None:
        path = self.path(inst, format)
        with tarfile.open(path, 'w:') as tar:
            # add main run script
            cfg_i = tarfile.TarInfo('guest/run.sh')
            cfg_i.mode = 0o777
            cfg_f = self.host.strfile(self.host._config_str(inst))
            cfg_f.seek(0, io.SEEK_END)
            cfg_i.size = cfg_f.tell()
            cfg_f.seek(0, io.SEEK_SET)
            tar.addfile(tarinfo=cfg_i, fileobj=cfg_f)
            cfg_f.close()

            # add additional config files
            for (n, f) in self.host.config_files(inst).items():
                f_i = tarfile.TarInfo('guest/' + n)
                f_i.mode = 0o777
                f.seek(0, io.SEEK_END)
                f_i.size = f.tell()
                f.seek(0, io.SEEK_SET)
                tar.addfile(tarinfo=f_i, fileobj=f)
                f.close()



# This is an additional example: building disk images directly from python
# Could of course also have a version that generates the packer config from
# python
class PackerDiskImage(DynamicDiskImage):
    def __init__(self, h: 'FullSystemHost', packer_config_path: str) -> None:
        super().__init__(h)
        self.config_path = packer_config_path

    def available_formats(self) -> list[str]:
        return ["raw", "qcow"]

    async def prepare_image_path(self, inst: inst_base.Instantiation, format: str) -> str:
        # TODO: invoke packer to build the image if necessary
        pass

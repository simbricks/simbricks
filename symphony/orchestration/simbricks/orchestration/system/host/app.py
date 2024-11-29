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

import typing as tp
import abc
import io
from simbricks.orchestration.instantiation import base as inst_base
from simbricks.utils import base as utils_base
from simbricks.orchestration.system import base as sys_base

if tp.TYPE_CHECKING:
    from simbricks.orchestration.system import host as sys_host


class Application(utils_base.IdObj):
    def __init__(self, h: sys_host.Host) -> None:
        super().__init__()
        self.host: sys_host.Host = h

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["type"] = self.__class__.__name__
        json_obj["module"] = self.__class__.__module__
        json_obj["host"] = self.host.id()
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict):
        instance = super().fromJSON(json_obj)
        host_id = utils_base.get_json_attr_top(json_obj, "host")
        instance.host = system.get_comp(host_id)
        return instance


# Note AK: Maybe we can factor most of the duplicate calls with the host out
# into a separate module.
class BaseLinuxApplication(Application):
    def __init__(self, h: sys_host.LinuxHost) -> None:
        super().__init__(h)
        self.start_delay: float | None = None
        self.end_delay: float | None = None
        self.wait: bool = False

    @abc.abstractmethod
    def run_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        """Commands to run on node."""
        raise Exception("must be overwritten")

    def cleanup_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        """Commands to run to cleanup node."""
        if self.end_delay is None:
            return []
        else:
            return [f"sleep {self.start_delay}"]

    def config_files(self, inst: inst_base.Instantiation) -> dict[str, tp.IO]:
        """
        Additional files to put inside the node, which are mounted under
        `/tmp/guest/`.

        Specified in the following format: `filename_inside_node`:
        `IO_handle_of_file`
        """
        return {}

    def prepare_pre_cp(self, inst: inst_base.Instantiation) -> list[str]:
        """Commands to run to prepare node before checkpointing."""
        return []

    def prepare_post_cp(self, inst: inst_base.Instantiation) -> list[str]:
        """Commands to run to prepare node after checkpoint restore."""
        if self.end_delay is None:
            return []
        else:
            return [f"sleep {self.end_delay}"]

    def strfile(self, s: str) -> io.BytesIO:
        """
        Helper function to convert a string to an IO handle for usage in
        `config_files()`.

        Using this, you can create a file with the string as its content on the
        simulated node.
        """
        return io.BytesIO(bytes(s, encoding="UTF-8"))

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["start_delay"] = self.start_delay
        json_obj["end_delay"] = self.end_delay
        json_obj["wait"] = self.wait
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict):
        instance = super().fromJSON(system, json_obj)
        instance.start_delay = utils_base.get_json_attr_top_or_none(
            json_obj, "start_delay"
        )
        instance.end_delay = utils_base.get_json_attr_top_or_none(json_obj, "end_delay")
        instance.wait = utils_base.get_json_attr_top(json_obj, "wait")
        return instance


class PingClient(BaseLinuxApplication):
    def __init__(self, h: sys_host.LinuxHost, server_ip: str = "192.168.64.1") -> None:
        super().__init__(h)
        self.server_ip: str = server_ip

    def run_cmds(self, inst: inst_base.Instantiation) -> tp.List[str]:
        return [f"ping {self.server_ip} -c 10"]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["server_ip"] = self.server_ip
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict):
        instance = super().fromJSON(system, json_obj)
        instance.server_ip = utils_base.get_json_attr_top(json_obj, "server_ip")
        return instance


class Sleep(BaseLinuxApplication):
    def __init__(
        self, h: sys_host.LinuxHost, delay: float = 10, infinite: bool = False
    ) -> None:
        super().__init__(h)
        self.infinite: bool = infinite
        self.delay: float = delay

    def run_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        if self.infinite:
            return [f"sleep infinity"]
        return [f"sleep {self.delay}"]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["infinite"] = self.infinite
        json_obj["delay"] = self.delay
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> Sleep:
        instance = super().fromJSON(system, json_obj)
        instance.infinite = bool(utils_base.get_json_attr_top(json_obj, "infinite"))
        instance.delay = float(utils_base.get_json_attr_top(json_obj, "delay"))
        return instance


class NetperfServer(BaseLinuxApplication):
    def __init__(self, h: sys_host.LinuxHost) -> None:
        super().__init__(h)

    def run_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        return ["netserver", "sleep infinity"]

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> NetperfServer:
        return super().fromJSON(system, json_obj)


class NetperfClient(BaseLinuxApplication):
    def __init__(self, h: sys_host.LinuxHost, server_ip: str = "192.168.64.1") -> None:
        super().__init__(h)
        self.server_ip: str = server_ip
        self.duration_tp: int = 10
        self.duration_lat: int = 10

    def run_cmds(self, inst: inst_base.Instantiation) -> list[str]:
        return [
            "netserver",
            "sleep 0.5",
            f"netperf -H {self.server_ip} -l {self.duration_tp}",
            (
                f"netperf -H {self.server_ip} -l {self.duration_lat} -t TCP_RR"
                " -- -o mean_latency,p50_latency,p90_latency,p99_latency"
            ),
        ]

    def toJSON(self) -> dict:
        json_obj = super().toJSON()
        json_obj["server_ip"] = self.server_ip
        json_obj["duration_tp"] = self.duration_tp
        json_obj["duration_lat"] = self.duration_lat
        return json_obj

    @classmethod
    def fromJSON(cls, system: sys_base.System, json_obj: dict) -> NetperfClient:
        instance = super().fromJSON(system, json_obj)
        instance.server_ip = utils_base.get_json_attr_top(json_obj, "server_ip")
        instance.duration_tp = int(
            utils_base.get_json_attr_top(json_obj, "duration_tp")
        )
        instance.duration_lat = int(
            utils_base.get_json_attr_top(json_obj, "duration_lat")
        )
        return instance

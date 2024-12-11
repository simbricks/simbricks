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


import aiohttp
import typing
import contextlib
import asyncio
import json
from rich.console import Console
from .auth import TokenProvider
from .settings import client_settings
from simbricks.orchestration import system
from simbricks.orchestration import simulation


class BaseClient:
    def __init__(self, base_url=client_settings().base_url):
        self._base_url = base_url
        self._token_provider = TokenProvider()

    async def _get_headers(self, overwrite_headers: dict[str, typing.Any] | None = None) -> dict:
        headers = {}
        token = await self._token_provider.access_token()
        headers["Authorization"] = f"Bearer {token}"

        if overwrite_headers:
            headers.update(overwrite_headers)
            headers = {k: v for k, v in headers.items() if v is not None}

        return headers

    def build_url(self, url: str) -> str:
        return f"{self._base_url}{url}"

    @contextlib.asynccontextmanager
    async def session(
        self, overwrite_headers: dict[str, typing.Any] | None = None
    ) -> typing.AsyncIterator[aiohttp.ClientSession]:
        headers = await self._get_headers(overwrite_headers=overwrite_headers)
        session = aiohttp.ClientSession(headers=headers)
        try:
            yield session
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def post(
        self,
        url: str,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session() as session:
            async with session.post(
                url=self.build_url(url), data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                # print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def put(
        self,
        url: str,
        overwrite_headers: dict[str, typing.Any] | None = None,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session(overwrite_headers=overwrite_headers) as session:
            async with session.put(
                url=self.build_url(url), data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                # print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def patch(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session() as session:
            async with session.patch(
                url=self.build_url(url), data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                # print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session() as session:
            async with session.get(
                url=self.build_url(url), data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                # print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def delete(self, url: str, **kwargs: typing.Any) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session() as session:
            async with session.delete(url=self.build_url(url), **kwargs) as resp:  # TODO: handel connection error
                # print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    async def info(self):
        async with self.get(url="/info") as resp:
            return await resp.json()


class AdminClient:

    def __init__(self, base_client: BaseClient = BaseClient()):
        self._base_client = base_client

    def _prefix(self, url: str) -> str:
        return f"/admin{url}"

    async def get_ns(self, ns_id: int):
        async with self._base_client.get(url=self._prefix(f"/{ns_id}")) as resp:
            return await resp.json()

    async def get_all_ns(self):
        async with self._base_client.get(url=self._prefix("/")) as resp:
            return await resp.json()

    async def create_ns(self, parent_id: int | None, name: str):
        namespace_json = {"name": name}
        if parent_id:
            namespace_json["parent_id"] = parent_id
        async with self._base_client.post(url=self._prefix("/"), json=namespace_json) as resp:
            return await resp.json()

    async def delete(self, ns_id: int):
        async with self._base_client.delete(url=self._prefix(f"/{ns_id}")) as resp:
            return await resp.json()


class NSClient:
    def __init__(self, base_client: BaseClient = BaseClient(), namespace: str = ""):
        self._base_client: BaseClient = base_client
        self._namespace = namespace

    def _build_ns_prefix(self, url: str) -> str:
        return f"/ns/{self._namespace}/-{url}"

    @contextlib.asynccontextmanager
    async def post(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.post(url=self._build_ns_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self,
        url: str,
        overwrite_headers: dict[str, typing.Any] | None = None,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.put(
            url=self._build_ns_prefix(url=url), overwrite_headers=overwrite_headers, data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def patch(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.patch(url=self._build_ns_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        async with self._base_client.get(url=self._build_ns_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def delete(self, url: str, **kwargs: typing.Any) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.delete(url=self._build_ns_prefix(url=url), **kwargs) as resp:
            yield resp

    async def info(self):
        async with self.get(url="/info") as resp:
            return await resp.json()

    async def create(self, parent_id: int, name: str):
        namespace_json = {"parent_id": parent_id, "name": name}
        async with self.post(url="/", json=namespace_json) as resp:
            return await resp.json()

    async def delete_ns(self, ns_id: int):
        async with self.delete(url=self._build_ns_prefix(f"/{ns_id}")) as _:
            return

    # retrieve namespace ns_id, useful for retrieving a child the current namespace
    async def get_ns(self, ns_id: int):
        async with self.get(url=f"/one/{ns_id}") as resp:
            return await resp.json()

    # retrieve the current namespace
    async def get_cur(self):
        async with self.get(url="/") as resp:
            return await resp.json()

    # recursively retrieve all namespaces beginning with the current including all children
    async def get_all(self):
        async with self.get(url="/all") as resp:
            return await resp.json()


class SimBricksClient:

    def __init__(self, ns_client: NSClient = NSClient()) -> None:
        self._ns_client: NSClient = ns_client

    async def info(self):
        async with self._ns_client.get("/systems/info") as resp:
            return await resp.json()

    async def create_system(self, system: system.System) -> dict:
        sys_json = json.dumps(system.toJSON())
        json_obj = {"sb_json": sys_json}
        async with self._ns_client.post(url="/systems", json=json_obj) as resp:
            return await resp.json()

    async def delete_system(self, sys_id: int):
        async with self._ns_client.delete(url=f"/systems/{sys_id}") as resp:
            return await resp.json()

    async def get_systems(self) -> list[dict]:
        async with self._ns_client.get(url="/systems") as resp:
            return await resp.json()

    async def get_system(self, system_id: int) -> dict:
        async with self._ns_client.get(url=f"/systems/{system_id}") as resp:
            return await resp.json()

    async def create_simulation(self, system_db_id: int, simulation: simulation.Simulation) -> simulation.Simulation:
        sim_js = json.dumps(simulation.toJSON())
        json_obj = {"system_id": system_db_id, "sb_json": sim_js}
        async with self._ns_client.post(url="/simulations", json=json_obj) as resp:
            return await resp.json()

    async def delete_simulation(self, sim_id: int):
        async with self._ns_client.delete(url=f"/simulations/{sim_id}") as resp:
            return await resp.json()

    async def get_simulation(self, simulation_id: int) -> dict:
        async with self._ns_client.get(url=f"/simulations/{simulation_id}") as resp:
            return await resp.json()

    async def get_simulations(self) -> list[dict]:
        async with self._ns_client.get(url="/simulations") as resp:
            return await resp.json()

    async def create_instantiation(self, sim_db_id: int, instantiation: simulation.Simulation) -> simulation.Simulation:
        inst_json = json.dumps({})  # FIXME
        json_obj = {"simulation_id": sim_db_id, "sb_json": inst_json}
        async with self._ns_client.post(url="/instantiations", json=json_obj) as resp:
            return await resp.json()

    async def delete_instantiation(self, inst_id: int):
        async with self._ns_client.delete(url=f"/instantiations/{inst_id}") as resp:
            return await resp.json()

    async def get_instantiation(self, instantiation_id: int) -> dict:
        async with self._ns_client.get(url=f"/instantiations/{instantiation_id}") as resp:
            return await resp.json()

    async def get_instantiations(self) -> list[dict]:
        async with self._ns_client.get(url="/instantiations") as resp:
            return await resp.json()

    async def create_run(self, inst_db_id: int) -> dict:
        json_obj = {
            "instantiation_id": inst_db_id,
            "state": "pending",
            "output": "",
        }
        async with self._ns_client.post(url="/runs", json=json_obj) as resp:
            return await resp.json()

    async def delete_run(self, rid: int):
        async with self._ns_client.delete(url=f"/runs/{rid}") as resp:
            return await resp.json()

    async def update_run(self, rid: int, updates: dict[str, typing.Any] = {"state": "pending"}) -> dict:
        async with self._ns_client.patch(url=f"/runs/{rid}", json=updates) as resp:
            return await resp.json()

    async def get_run(self, run_id: int) -> dict:
        async with self._ns_client.get(url=f"/runs/{run_id}") as resp:
            return await resp.json()

    async def get_runs(self) -> list[dict]:
        async with self._ns_client.get(url=f"/runs") as resp:
            return await resp.json()

    async def follow_run(self, run_id: int) -> None:
        console = Console()
        with console.status(f"[bold green]Waiting for run {run_id} to finish...") as status:
            last_run = None
            prev_len = 0
            while True:
                run = await self.get_run(run_id)

                if not last_run or last_run["state"] != run["state"]:
                    console.log(f"Run State:", run["state"])

                if not last_run or (len(last_run["output"]) != len(run["output"]) and len(run["output"]) != 0):
                    prev_len = len(last_run["output"]) if last_run else 0
                    # console.log(run["output"][prev_len:])
                    console.log(run["output"]) # TODO: FIXME

                # did we finish?
                if run["state"] != "pending" and run["state"] != "running":
                    break

                last_run = run
                await asyncio.sleep(15)

        console.log("Run {run_id} finished")

    async def set_run_input(self, rid: int, uploaded_input_file: str):
        with open(uploaded_input_file, "rb") as f:
            file_data = {"file": f}
            async with self._ns_client.put(url=f"/runs/input/{rid}", data=file_data) as resp:
                return await resp.json()

    async def get_run_input(self, rid: int, store_path: str):
        async with self._ns_client.post(url=f"/runs/input/{rid}") as resp:
            content = await resp.read()
            with open(store_path, "wb") as f:
                f.write(content)

    async def set_run_artifact(self, rid: int, uploaded_output_file: str):
        with open(uploaded_output_file, "rb") as f:
            file_data = {"file": f}
            async with self._ns_client.put(url=f"/runs/output/{rid}", data=file_data) as resp:
                return await resp.json()

    async def get_run_artifact(self, rid: int, store_path: str):
        async with self._ns_client.post(url=f"/runs/output/{rid}") as resp:
            content = await resp.read()
            with open(store_path, "wb") as f:
                f.write(content)


class RunnerClient:

    def __init__(self, ns_client, id: int) -> None:
        self._ns_client: NSClient = ns_client
        self._runner_id = id

    def _build_prefix(self, url: str) -> str:
        return f"/runners/{self._runner_id}{url}"

    @contextlib.asynccontextmanager
    async def post(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.post(url=self._build_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.put(url=self._build_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        async with self._ns_client.get(url=self._build_prefix(url=url), data=data, **kwargs) as resp:
            yield resp

    async def next_run(self) -> dict | None:
        async with self.get(f"/next_run") as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 202:
                return None
            else:
                resp.raise_for_status()

    async def update_run(
        self,
        run_id: int,
        state: str,
        output: str,
    ) -> None:
        obj = {
            "state": state,
            "output": output,
            "id": run_id,
            "instantiation_id": 42,
        }
        async with self.put(url=f"/update_run/{run_id}", json=obj) as resp:
            ret = await resp.json()


    async def send_out(
        self,
        run_id: int,
        simulator: str,
        stderr: bool,
        output: list[str],
    ) -> None:
        objs = []
        for line in output:
            obj = {
                "run_id": run_id,
                "simulator": simulator,
                "stderr": stderr,
                "output": line,
            }
            objs.append[obj]
        async with self.post(url=f"/{run_id}/console", json=objs) as resp:
            ret = await resp.json()

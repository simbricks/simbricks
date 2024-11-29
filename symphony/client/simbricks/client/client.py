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
from .auth import TokenProvider
from simbricks.orchestration import system
from simbricks.orchestration import simulation
from simbricks.orchestration import instantiation


class BaseClient:
    def __init__(self, base_url="https://app.simbricks.io/api"):
        self._base_url = base_url
        self._token_provider = TokenProvider()

    async def _get_headers(self) -> dict:
        headers = {}
        token = await self._token_provider.access_token()
        headers["Authorization"] = f"Bearer {token}"
        headers["accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        return headers

    @contextlib.asynccontextmanager
    async def session(self) -> typing.AsyncIterator[aiohttp.ClientSession]:
        headers = await self._get_headers()
        session = aiohttp.ClientSession(headers=headers)
        try:
            yield session
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def post(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        url = f"{self._base_url}{url}"

        async with self.session() as session:
            async with session.post(
                url=url, data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def put(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        url = f"{self._base_url}{url}"

        async with self.session() as session:
            async with session.put(
                url=url, data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                print(await resp.text())
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        url = f"{self._base_url}{url}"
        async with self.session() as session:
            async with session.get(
                url=url, data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                resp.raise_for_status()  # TODO: handel gracefully
                yield resp

    async def info(self):
        async with self.get(url="/info") as resp:
            return await resp.json()


class NSClient:
    def __init__(self, base_client: BaseClient = BaseClient(), namespace: str = ""):
        self._base_client: BaseClient = base_client
        self._namespace = namespace
        self._session: aiohttp.ClientSession | None = None

    def _build_ns_prefix(self, url: str) -> str:
        return f"/ns/{self._namespace}/-{url}"

    @contextlib.asynccontextmanager
    async def post(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.post(
            url=self._build_ns_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.put(
            url=self._build_ns_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        async with self._base_client.get(
            url=self._build_ns_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    async def info(self):
        async with self.get(url="/info") as resp:
            return await resp.json()


class SimBricksClient:

    def __init__(self, ns_client: NSClient = NSClient()) -> None:
        self._ns_client: NSClient = ns_client

    async def info(self):
        async with self._ns_client.get("/systems/info") as resp:
            return await resp.json()

    async def create_system(self, system: system.System) -> dict:
        json_obj = {"sb_json": system.toJSON()}
        async with self._ns_client.post(url="/systems", json=json_obj) as resp:
            return await resp.json()

    async def get_systems(self) -> list[dict]:
        async with self._ns_client.get(url="/systems") as resp:
            return await resp.json()

    async def get_system(self, system_id: int) -> dict:
        async with self._ns_client.get(url=f"/systems/{system_id}") as resp:
            return await resp.json()

    async def create_simulation(
        self, system_db_id: int, simulation: simulation.Simulation
    ) -> simulation.Simulation:
        json_obj = {
            "system_id": system_db_id, 
            "sb_json": simulation.toJSON()
        }
        print(json_obj)
        async with self._ns_client.post(url="/simulations", json=json_obj) as resp:
            return await resp.json()

    async def get_simulation(self, simulation_id: int) -> dict:
        async with self._ns_client.get(url=f"/simulations/{simulation_id}") as resp:
            return await resp.json()
        
    async def get_simulations(self) -> list[dict]:
        async with self._ns_client.get(url="/simulations") as resp:
            return await resp.json()

    async def create_instantiation(
        self, sim_db_id: int, instantiation: simulation.Simulation
    ) -> simulation.Simulation:
        json_obj = {
            "simulation_id": sim_db_id,
            "sb_json": {} # FIXME
        }
        print(json_obj)
        async with self._ns_client.post(url="/instantiations", json=json_obj) as resp:
            return await resp.json()

    async def get_instantiation(
        self, instantiation_id: int
    ) -> instantiation.Instantiation:
        async with self._ns_client.get(url=f"/instantiations/{instantiation_id}") as resp:
            return await resp.json()

    async def create_run(
        self, inst_db_id: int
    ) -> dict:
        json_obj = {
            "instantiation_id": inst_db_id,
            "state": "pending",
            "output": "",
        }
        async with self._ns_client.post(url="/runs", json=json_obj) as resp:
            return await resp.json()

    async def get_run(self, run_id: int) -> dict:
        async with self._ns_client.get(url=f"/runs/{run_id}") as resp:
            return await resp.json()

    async def get_runs(self) -> [dict]:
        async with self._ns_client.get(url=f"/runs") as resp:
            return await resp.json()



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
        async with self._ns_client.post(
            url=self._build_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.put(
            url=self._build_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def get(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:

        async with self._ns_client.get(
            url=self._build_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp


    async def next_run(
        self
    ) -> dict | None:
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
            'state': state,
            'output': output,
            'id': run_id,
            'instantiation_id': 42,
        }
        async with self.put(url=f"/update_run/{run_id}", json=obj) as resp:
            ret = await resp.json()
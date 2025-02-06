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
import datetime
import typing
import typing_extensions
import contextlib
import json
import warnings
from simbricks.utils import base as utils_base
from .auth import Token, TokenProvider
from .settings import client_settings
from simbricks.orchestration import system
from simbricks.orchestration import simulation
from simbricks.orchestration import instantiation
from simbricks.schemas import base as schemas


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
        timeout = aiohttp.ClientTimeout(total=client_settings().timeout_sec)
        session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        try:
            yield session
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def request(
        self, meth: str, url: str, data: typing.Any = None, retry: bool = True, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.session() as session:
            async with session.request(
                method=meth, url=self.build_url(url), data=data, **kwargs
            ) as resp:  # TODO: handel connection error
                if resp.status == 401 and "WWW-Authenticate" in resp.headers and retry:
                    wwa = resp.headers["WWW-Authenticate"]
                    parts = wwa.split(",")
                    ticket = None
                    for p in parts:
                        p = p.strip()
                        if p.startswith('ticket="'):
                            ticket = p[8:-1]

                    if ticket:
                        await self._token_provider.resource_token(ticket)
                        async with self.request(meth, url, data, False, **kwargs) as resp:
                            yield resp
                elif resp.status in [400, 402, 422]:
                    msg = await resp.json()
                    raise Exception(f"Error sending request: {msg}")
                else:
                    resp.raise_for_status()  # TODO: handel gracefully
                    yield resp

    @contextlib.asynccontextmanager
    async def get(
        self,
        url: str,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.request(meth=aiohttp.hdrs.METH_GET, url=url, data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def post(
        self,
        url: str,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.request(meth=aiohttp.hdrs.METH_POST, url=url, data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self,
        url: str,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.request(meth=aiohttp.hdrs.METH_PUT, url=url, data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def patch(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.request(meth=aiohttp.hdrs.METH_PATCH, url=url, data=data, **kwargs) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def delete(
        self, url: str, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self.request(meth=aiohttp.hdrs.METH_DELETE, url=url, **kwargs) as resp:
            yield resp

    async def info(self):
        async with self.get(url="/info") as resp:
            return await resp.json()


class AdminClient:

    def __init__(self, base_client: BaseClient = BaseClient()):
        self._base_client = base_client

    def _prefix(self, url: str) -> str:
        return f"/admin{url}"

    async def get_ns(self, ns_id: int) -> schemas.ApiNamespace:
        async with self._base_client.get(url=self._prefix(f"/{ns_id}")) as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespace.model_validate(raw_json)

    async def get_all_ns(self) -> list[schemas.ApiNamespace]:
        async with self._base_client.get(url=self._prefix("/")) as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespaceList_A.validate_python(raw_json)

    async def create_ns(self, parent_id: int | None, name: str) -> schemas.ApiNamespace:
        ns = schemas.ApiNamespace.model_validate({"name": name, "parent_id": parent_id})
        async with self._base_client.post(
            url=self._prefix("/"), json=ns.model_dump(exclude_none=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespace.model_validate(raw_json)

    async def delete(self, ns_id: int) -> None:
        async with self._base_client.delete(url=self._prefix(f"/{ns_id}")) as _:
            pass

    async def schedule_ns(self, ns_id: int) -> None:
        async with self._base_client.post(url=self._prefix(f"/{ns_id}/schedule")) as _:
            pass


class OrgClient:

    def __init__(self, base_client: BaseClient = BaseClient()):
        self._base_client = base_client

    def _prefix(self, org: str, url: str) -> str:
        return f"/org/{org}{url}"

    async def get_members(self, org: str):
        async with self._base_client.get(url=self._prefix(org, f"/members")) as resp:
            return await resp.json()

    async def invite_member(self, org: str, email: str, first_name: str, last_name: str):
        namespace_json = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        async with self._base_client.post(
            url=self._prefix(org, "/invite-member"), json=namespace_json
        ) as resp:
            await resp.json()

    async def create_guest(self, org: str, email: str, first_name: str, last_name: str):
        namespace_json = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        }
        async with self._base_client.post(
            url=self._prefix(org, "/create-guest"), json=namespace_json
        ) as resp:
            await resp.json()

    async def guest_token(self, org: str, email: str) -> Token:
        j = {
            "email": email,
        }
        async with self._base_client.post(url=self._prefix(org, "/guest-token"), json=j) as resp:
            tok = await resp.json()
            return Token.parse_from_resp(tok)

    async def guest_magic_link(self, org: str, email: str) -> str:
        j = {
            "email": email,
        }
        async with self._base_client.post(
            url=self._prefix(org, "/guest-magic-link"), json=j
        ) as resp:
            return (await resp.json())["magic_link"]


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
        async with self._base_client.post(
            url=self._build_ns_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def put(
        self,
        url: str,
        data: typing.Any = None,
        **kwargs: typing.Any,
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.put(
            url=self._build_ns_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def patch(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.patch(
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

    @contextlib.asynccontextmanager
    async def delete(
        self, url: str, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._base_client.delete(url=self._build_ns_prefix(url=url), **kwargs) as resp:
            yield resp

    async def create(self, parent_id: int, name: str) -> schemas.ApiNamespace:
        ns = schemas.ApiNamespace.model_validate({"parent_id": parent_id, "name": name})
        async with self.post(url="/", json=ns.model_dump(exclude_unset=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespace.model_validate(raw_json)

    async def delete_ns(self, ns_id: int) -> None:
        async with self.delete(url=self._build_ns_prefix(f"/{ns_id}")) as _:
            pass

    # retrieve namespace ns_id, useful for retrieving a child the current namespace
    async def get_ns(self, ns_id: int) -> schemas.ApiNamespace:
        async with self.get(url=f"/one/{ns_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespace.model_validate(raw_json)

    # retrieve the current namespace
    async def get_cur(self) -> schemas.ApiNamespace:
        async with self.get(url="/") as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespace.model_validate(raw_json)

    # recursively retrieve all namespaces beginning with the current including all children
    async def get_all(self) -> list[schemas.ApiNamespace]:
        async with self.get(url="/all") as resp:
            raw_json = await resp.json()
            return schemas.ApiNamespaceList_A.validate_python(raw_json)

    async def get_members(self) -> dict[str, list[dict]]:
        async with self.get(url="/members") as resp:
            return await resp.json()

    async def get_role_members(self, role: str) -> list[dict]:
        async with self.get(url=f"/members/{role}") as resp:
            return await resp.json()

    async def add_member(self, role: str, username: str) -> None:
        req_json = {"username": username}
        async with self.post(url=f"/members/{role}", json=req_json) as resp:
            await resp.json()


class SimBricksClient:

    def __init__(self, ns_client: NSClient = NSClient()) -> None:
        self._ns_client: NSClient = ns_client

    async def create_system(self, system: system.System) -> schemas.ApiSystem:
        sys_json = json.dumps(system.toJSON())
        sys = schemas.ApiSystem.model_validate({"sb_json": sys_json})
        async with self._ns_client.post(
            url="/systems", json=sys.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiSystem.model_validate(raw_json)

    async def delete_system(self, sys_id: int) -> None:
        async with self._ns_client.delete(url=f"/systems/{sys_id}") as _:
            pass

    async def get_systems(self) -> list[schemas.ApiSystem]:
        async with self._ns_client.get(url="/systems") as resp:
            raw_json = await resp.json()
            return schemas.ApiSystemList_A.validate_python(raw_json)

    async def get_system(self, system_id: int) -> schemas.ApiSystem:
        async with self._ns_client.get(url=f"/systems/{system_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiSystem.model_validate(raw_json)

    async def create_simulation(
        self, system_db_id: int, simulation: simulation.Simulation
    ) -> schemas.ApiSimulation:
        sim_js = json.dumps(simulation.toJSON())
        sim = schemas.ApiSimulation.model_validate({"system_id": system_db_id, "sb_json": sim_js})
        async with self._ns_client.post(
            url="/simulations", json=sim.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiSimulation.model_validate(raw_json)

    async def delete_simulation(self, sim_id: int) -> None:
        async with self._ns_client.delete(url=f"/simulations/{sim_id}") as _:
            pass

    async def get_simulation(self, simulation_id: int) -> schemas.ApiSimulation:
        async with self._ns_client.get(url=f"/simulations/{simulation_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiSimulation.model_validate(raw_json)

    async def get_simulations(self) -> list[schemas.ApiSimulation]:
        async with self._ns_client.get(url="/simulations") as resp:
            raw_json = await resp.json()
            return schemas.ApiSimulationList_A.validate_python(raw_json)

    async def create_instantiation(
        self, sim_db_id: int, instantiation: instantiation.Instantiation
    ) -> schemas.ApiInstantiation:
        inst_json = json.dumps(instantiation.toJSON())
        inst = schemas.ApiInstantiation.model_validate(
            {"simulation_id": sim_db_id, "sb_json": inst_json}
        )
        async with self._ns_client.post(
            url="/instantiations", json=inst.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiInstantiation.model_validate(raw_json)

    async def delete_instantiation(self, inst_id: int) -> None:
        async with self._ns_client.delete(url=f"/instantiations/{inst_id}") as _:
            pass

    async def get_instantiation(self, instantiation_id: int) -> schemas.ApiInstantiation:
        async with self._ns_client.get(url=f"/instantiations/{instantiation_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiInstantiation.model_validate(raw_json)

    async def get_instantiations(self) -> list[schemas.ApiInstantiation]:
        async with self._ns_client.get(url="/instantiations") as resp:
            raw_json = await resp.json()
            return schemas.ApiInstantiationList_A.validate_python(raw_json)

    async def create_run(self, inst_db_id: int) -> schemas.ApiRun:
        run = schemas.ApiRun.model_validate(
            {
                "instantiation_id": inst_db_id,
                "state": schemas.RunState.PENDING,
            }
        )
        async with self._ns_client.post(
            url="/runs", json=run.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiRun.model_validate(raw_json)

    async def delete_run(self, rid: int) -> None:
        async with self._ns_client.delete(url=f"/runs/{rid}") as _:
            pass

    async def update_run(
        self,
        rid: int,
        instantiation_id: int | None = None,
        state: schemas.RunState | None = None,
        output: str | None = None,
    ) -> schemas.ApiRun:
        update = schemas.ApiRun.model_validate(
            {
                "instantiation_id": instantiation_id,
                "state": state,
                "output": output,
            }
        )
        async with self._ns_client.patch(
            url=f"/runs/{rid}", json=update.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiRun.model_validate(raw_json)

    async def get_run(self, run_id: int) -> schemas.ApiRun:
        async with self._ns_client.get(url=f"/runs/{run_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiRun.model_validate(raw_json)

    async def get_runs(self) -> list[schemas.ApiRun]:
        async with self._ns_client.get(url=f"/runs") as resp:
            raw_json = await resp.json()
            return schemas.ApiRunList_A.validate_python(raw_json)

    async def set_run_input(self, rid: int, uploaded_input_file: str) -> None:
        with open(uploaded_input_file, "rb") as f:
            file_data = {"file": f}
            async with self._ns_client.put(url=f"/runs/input/{rid}", data=file_data) as _:
                pass

    async def get_run_input(self, rid: int, store_path: str) -> None:
        async with self._ns_client.post(url=f"/runs/input/{rid}") as resp:
            content = await resp.read()
            with open(store_path, "wb") as f:
                f.write(content)

    async def set_run_artifact(self, rid: int, uploaded_output_file: str) -> None:
        with open(uploaded_output_file, "rb") as f:
            file_data = {"file": f}
            async with self._ns_client.put(url=f"/runs/output/{rid}", data=file_data) as resp:
                await resp.json()

    async def get_run_artifact(self, rid: int, store_path: str) -> None:
        async with self._ns_client.post(url=f"/runs/output/{rid}") as resp:
            content = await resp.read()
            with open(store_path, "wb") as f:
                f.write(content)

    async def get_run_console(
        self, rid: int, simulators_seen_until: dict[int, datetime.datetime] = {}
    ) -> schemas.ApiRunOutput:
        simulators = {}
        # TODO: use pydantic model...
        for simulator_id, until in simulators_seen_until.items():
            simulators[simulator_id] = until.isoformat()
        obj = {"simulators": simulators}
        async with self._ns_client.get(url=f"/runs/{rid}/console", json=obj) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunOutput.model_validate(raw_json)


class ResourceGroupClient:

    def __init__(self, ns_client) -> None:
        self._ns_client: NSClient = ns_client

    async def create_rg(
        self, label: str, available_cores: int, available_memory: int
    ) -> schemas.ApiResourceGroup:
        to_create = schemas.ApiResourceGroup.model_validate(
            {
                "label": label,
                "available_cores": available_cores,
                "available_memory": available_memory,
            }
        )
        async with self._ns_client.post(url="/resource_group", json=to_create.model_dump()) as resp:
            raw_json = await resp.json()
            return schemas.ApiResourceGroup.model_validate(raw_json)

    async def update_rg(
        self,
        rg_id: int,
        label: str | None = None,
        available_cores: int | None = None,
        available_memory: int | None = None,
        cores_left: int | None = None,
        memory_left: int | None = None,
    ) -> schemas.ApiResourceGroup:
        update = schemas.ApiResourceGroup.model_validate(
            {
                "id": rg_id,
                "label": label,
                "available_cores": available_cores,
                "available_memory": available_memory,
                "cores_left": cores_left,
                "memory_left": memory_left,
            }
        )
        async with self._ns_client.put(
            url=f"/resource_group/{rg_id}", json=update.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiResourceGroup.model_validate(raw_json)

    async def get_rg(self, rg_id: int) -> schemas.ApiResourceGroup:
        async with self._ns_client.get(url=f"/resource_group/{rg_id}") as resp:
            raw_json = await resp.json()
            return schemas.ApiResourceGroup.model_validate(raw_json)

    async def filter_get_rg(
        self,
    ) -> list[schemas.ApiResourceGroup]:  # TODO: add filtering object...
        async with self._ns_client.get(url=f"/resource_group") as resp:
            raw_json = await resp.json()
            return schemas.ApiResourceGroupList_A.validate_python(raw_json)


class RunnerClient:

    def __init__(self, ns_client, id: int) -> None:
        self._ns_client: NSClient = ns_client
        self.runner_id = id

    def _build_prefix(self, url: str) -> str:
        return f"/runners/{self.runner_id}{url}"

    @contextlib.asynccontextmanager
    async def post(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.post(
            url=self._build_prefix(url=url), data=data, **kwargs
        ) as resp:
            yield resp

    @contextlib.asynccontextmanager
    async def delete(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.delete(
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
    async def patch(
        self, url: str, data: typing.Any = None, **kwargs: typing.Any
    ) -> typing.AsyncIterator[aiohttp.ClientResponse]:
        async with self._ns_client.patch(
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

    async def create_runner(
        self, resource_group_id: int, label: str, tags: list[str]
    ) -> schemas.ApiRunner:
        tags_obj = list(map(lambda t: {"label": t}, tags))
        runner = schemas.ApiRunner.model_validate(
            {"resource_group_id": resource_group_id, "label": label, "tags": tags_obj}
        )
        async with self._ns_client.post(url=f"/runners", json=runner.model_dump()) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunner.model_validate(raw_json)

    async def runner_started(self) -> None:
        async with self.post(url="/started") as _:
            pass

    @typing_extensions.deprecated(
        "The `create_runner_event` method is deprectaed; use `create_events` instead."
    )
    async def create_runner_event(self, action: str, run_id: int | None) -> schemas.ApiRunnerEvent:
        warnings.warn(
            "The `create_runner_event` method is deprectaed; use `create_events` instead."
        )
        event = schemas.ApiRunnerEvent.model_validate(
            {"runner_id": self.runner_id, "action": action, "run_id": run_id}
        )
        async with self.post(url=f"/events", json=event.model_dump()) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunnerEvent.model_validate(raw_json)

    @typing_extensions.deprecated(
        "The `delete_runner_event` method is deprectaed; use `delete_events` instead."
    )
    async def delete_runner_event(self, event_id: int) -> None:
        warnings.warn(
            "The `delete_runner_event` method is deprectaed; use `delete_events` instead."
        )
        async with self.delete(url=f"/events/{event_id}") as _:
            pass

    @typing_extensions.deprecated(
        "The `update_runner_event` method is deprecated; use `update_events` istead."
    )
    async def update_runner_event(
        self,
        event_id: int,
        action: str | None,
        run_id: int | None,
        event_status: schemas.ApiEventStatus | None,
    ) -> schemas.ApiRunnerEvent:
        warnings.warn("The `update_runner_event` method is deprecated; use `update_events` istead.")
        event = schemas.ApiRunnerEvent.model_validate(
            {
                "id": event_id,
                "runner_id": self.runner_id,
                "action": action,
                "run_id": run_id,
                "event_status": event_status,
            }
        )
        async with self.put(url=f"/events", json=event.model_dump(exclude_unset=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunnerEvent.model_validate(raw_json)

    @typing_extensions.deprecated(
        "The `get_events` method is deprecated; use `fetch_events` istead."
    )
    async def get_events(
        self,
        action: str | None,
        run_id: int | None,
        limit: int | None,
        event_status: schemas.ApiEventStatus | None,
    ) -> list[schemas.ApiRunnerEvent]:
        warnings.warn("The `get_events` method is deprecated; use `fetch_events` istead.")
        # TODO: introduce query object
        params = {
            "action": action,
            "run_id": run_id,
            "event_status": event_status.value,
            "limit": limit,
        }
        params = utils_base.filter_None_dict(to_filter=params)
        async with self.get(url=f"/events", params=params) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunnerEventList_A.validate_python(raw_json)

    async def update_runner(
        self,
        resource_group_id: int | None = None,
        label: str | None = None,
        tags: list[str] | None = None,
    ) -> schemas.ApiRunner:
        runner = schemas.ApiRunner.model_validate(
            {
                "resource_group_id": resource_group_id,
                "label": label,
                "tags": tags,
            }
        )
        async with self.post(url="", json=runner.model_dump(exclude_unset=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunner.model_validate(raw_json)

    async def delete_runner(self) -> None:
        async with self.delete(url="") as _:
            pass

    async def get_runner(self) -> schemas.ApiRunner:
        async with self.get(url=f"") as resp:
            raw_json = await resp.json()
            return schemas.ApiRunner.model_validate(raw_json)

    async def list_runners(self) -> list[schemas.ApiRunner]:
        async with self._ns_client.get(url=f"/runners") as resp:
            raw_json = await resp.json()
            return schemas.ApiRunnerList_A.validate_python(raw_json)

    async def send_heartbeat(self) -> None:
        async with self.put(url="/heartbeat") as _:
            pass

    async def filter_get_runs(
        self,
        run_id: int | None = None,
        instantiation_id: int | None = None,
        state: str | None = None,
        limit: int | None = None,
    ) -> list[schemas.ApiRun]:
        query = schemas.ApiRunQuery.model_validate(
            {
                "id": run_id,
                "instantiation_id": instantiation_id,
                "state": state,
                "limit": limit,
            }
        )
        async with self.post(
            url="/filter_get_run", json=query.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiRunList_A.validate_python(raw_json)

    async def next_run(self) -> schemas.ApiRun | None:
        async with self.get(f"/next_run") as resp:
            if resp.status == 200:
                raw_json = await resp.json()
                return schemas.ApiRun.model_validate(raw_json)
            elif resp.status == 202:
                return None
            else:
                resp.raise_for_status()

    async def update_run(
        self,
        run_id: int,
        state: schemas.RunState,
        output: str,
    ) -> schemas.ApiRun:
        run = schemas.ApiRun.model_validate(
            {
                "state": state,
                "output": output,
                "id": run_id,
            }
        )
        async with self.put(
            url=f"/update_run/{run_id}", json=run.model_dump(exclude_unset=True)
        ) as resp:
            raw_json = await resp.json()
            return schemas.ApiRun.model_validate(raw_json)

    @typing_extensions.deprecated(
        "The `update_events` method is deprecated; use `send_events` istead."
    )
    async def update_state_simulator(
        self, run_id: int, sim_id: int, sim_name: str, state: str, cmd: str
    ) -> None:
        warnings.warn("The `update_events` method is deprecated; use `send_events` istead.")
        obj = {
            "run_id": run_id,
            "simulator_id": sim_id,
            "simulator_name": sim_name,
            "state": state,
            "command": cmd,
        }
        async with self.post(url=f"/run/{run_id}/simulator/{sim_id}/state", json=obj) as _:
            pass

    @typing_extensions.deprecated(
        "The `update_proxy` method is deprecated; use `send_events` istead."
    )
    async def update_proxy(self, run_id: int, proxy_id: int, state: str, cmd: str) -> None:
        warnings.warn("The `update_proxy` method is deprecated; use `send_events` istead.")
        obj = {"run_id": run_id, "proxy_id": proxy_id, "state": state, "cmd": cmd}
        async with self.put(url=f"/{run_id}/proxy/{proxy_id}/state", json=obj) as _:
            pass

    @typing_extensions.deprecated(
        "The `send_out_simulation` method is deprecated; use `create_events` istead."
    )
    async def send_out_simulation(
        self,
        run_id: int,
        cmd: int,
        is_stderr: bool,
        output: list[str],
    ) -> None:
        warnings.warn("The `send_out_simulation` method is deprecated; use `create_events` istead.")
        objs = []
        for line in output:
            obj = {
                "run_id": run_id,
                "cmd": cmd,
                "is_stderr": is_stderr,
                "output": line,
            }
            objs.append(obj)
        async with self.post(url=f"/{run_id}/simulation/console", json=objs) as _:
            pass

    @typing_extensions.deprecated(
        "The `send_out_simulator` method is deprecated; use `create_events` istead."
    )
    async def send_out_simulator(
        self,
        run_id: int,
        sim_id: int,
        sim_name: str,
        is_stderr: bool,
        output: list[str],
        produced_at: datetime.datetime,
    ) -> None:
        warnings.warn("The `send_out_simulator` method is deprecated; use `create_events` istead.")
        objs = []
        for line in output:
            obj = {
                "run_id": run_id,
                "simulator_id": sim_id,
                "simulator_name": sim_name,
                "is_stderr": is_stderr,
                "output": line,
                "produced_at": produced_at.isoformat(),
            }
            objs.append(obj)
        async with self.post(url=f"/run/{run_id}/simulator/{sim_id}/console", json=objs) as _:
            pass

    @typing_extensions.deprecated(
        "The `send_out_proxy` method is deprecated; use `create_events` istead."
    )
    async def send_out_proxy(
        self,
        run_id: int,
        proxy_id: int,
        is_stderr: bool,
        output: list[str],
    ) -> None:
        warnings.warn("The `send_out_proxy` method is deprecated; use `create_events` istead.")
        objs = []
        for line in output:
            obj = {
                "run_id": run_id,
                "proxy_id": proxy_id,
                "is_stderr": is_stderr,
                "output": line,
            }
            objs.append(obj)
        async with self.post(url=f"/{run_id}/proxy/{proxy_id}/console", json=objs) as _:
            pass

    """
    GENERIC EVENT HANDLING INTERFACE
    """

    async def create_events(
        self, event_bundle: schemas.ApiEventBundle[schemas.ApiEventCreate_U]
    ) -> schemas.ApiEventBundle[schemas.ApiEventRead_U]:
        to_create = schemas.ApiEventBundle[schemas.ApiEventCreate_U].model_validate(event_bundle)
        async with self.post(url="/api/events", json=to_create.model_dump(exclude_none=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiEventBundle[schemas.ApiEventRead_U].model_validate(raw_json)

    async def fetch_events(
        self, to_fetch: schemas.ApiEventBundle[schemas.ApiEventQuery_U]
    ) -> schemas.ApiEventBundle[schemas.ApiEventRead_U]:
        query = schemas.ApiEventBundle[schemas.ApiEventQuery_U].model_validate(to_fetch)
        async with self.post(url="/api/events/fetch", json=query.model_dump(exclude_none=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiEventBundle[schemas.ApiEventRead_U].model_validate(raw_json)

    async def update_events(
        self, event_bundle: schemas.ApiEventBundle[schemas.ApiEventUpdate_U]
    ) -> schemas.ApiEventBundle[schemas.ApiEventRead_U]:
        to_update = schemas.ApiEventBundle[schemas.ApiEventUpdate_U].model_validate(event_bundle)
        async with self.patch(url="/api/events", json=to_update.model_dump(exclude_none=True)) as resp:
            raw_json = await resp.json()
            return schemas.ApiEventBundle[schemas.ApiEventRead_U].model_validate(raw_json)

    async def delete_events(
        self, event_bundle: schemas.ApiEventBundle[schemas.ApiEventDelete_U]
    ) -> None:
        to_delete = schemas.ApiEventBundle[schemas.ApiEventDelete_U].model_validate(event_bundle)
        async with self.delete(url="/api/events", json=to_delete.model_dump(exclude_none=True)) as _:
            pass

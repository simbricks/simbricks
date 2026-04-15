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

import json
import typing
from datetime import datetime
from pathlib import Path
from .base import base_client, validate_response_model
from .settings import client_settings
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.user import (
    user_default_membership,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.members import (
    members_modify,
    members_get,
    members_list,
    members_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.namespaces import (
    namespaces_children_create,
    namespaces_children_list,
    namespaces_get,
    namespaces_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.systems import (
    systems_create,
    systems_get,
    systems_list,
    systems_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.simulations import (
    simulations_create,
    simulations_get,
    simulations_list,
    simulations_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.instantiations import (
    instantiations_create,
    instantiations_get,
    instantitions_list,
    instantiations_delete,
    instantiations_input_artifact_get,
    instantiations_input_artifact_set,
    instantiations_fragment_input_artifact_get,
    instantiations_fragment_input_artifact_set,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.runs import (
    runs_create,
    runs_get,
    runs_list,
    runs_delete,
    runs_set,
    runs_console_list,
    runs_fragments_list,
    runs_fragments_output_artifact_get,
    runs_fragments_output_artifact_set,
    runs_sigusr1,
    runs_kill,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.resource_groups import (
    resource_groups_create,
    resource_groups_get,
    resource_groups_list,
    resource_groups_set,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.runners import (
    runners_create,
    runners_get,
    runners_list,
    runners_delete,
    runners_from_events_create,
    runners_to_events_list,
    runners_to_events_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    MembersList200Response,
    Namespace,
    NamespacesList200Response,
    NsMember,
    NsRole,
    System as ApiSystem,
    SystemsList200Response,
    Simulation as ApiSimulation,
    SimulationsList200Response,
    Instantiation as ApiInstantiation,
    Fragment as ApiFragment,
    InstantitionsList200Response,
    Run,
    RunState,
    RunsList200Response,
    RunsFragmentsList200Response,
    RunsConsoleList200Response,
    BodyInstantiationsInputArtifactSet,
    BodyInstantiationsFragmentInputArtifactSet,
    BodyRunsFragmentsOutputArtifactSet,
    ResourceGroup,
    ResourceGroupsList200Response,
    Runner,
    RunnersList200Response,
    RunnersFromEventsList200Response,
    RunnersToEventsList200Response,
    RunnersFromEventsCreateRequest,
    RunnerTag,
    FragmentOutputArtifact,
    FragmentStateChange,
    ProxyOutput,
    ProxyStateChange,
    RunnerHeartbeat,
    RunStatus,
    SimulatorOutput,
    SimulatorStateChange,
    KillRunReq,
    RunnerHeartbeatReq,
    StartRunReq,
    RunnerStarted,
    SimulationSigusr1,
    SimulatorChangedState,
    ProxyChangedState,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.types import File
from simbricks.orchestration.system import System as OrchSystem
from simbricks.orchestration.simulation import Simulation as OrchSimulation
from simbricks.orchestration.instantiation import Instantiation as OrchInstantiation


EventFromRunner_U = (
    RunnerStarted
    | RunnerHeartbeat
    | RunStatus
    | SimulatorOutput
    | SimulatorStateChange
    | ProxyOutput
    | ProxyStateChange
    | FragmentStateChange
    | FragmentOutputArtifact
)

EventToRunner_U = (
    RunnerHeartbeatReq
    | StartRunReq
    | KillRunReq
    | SimulationSigusr1
    | SimulatorChangedState
    | ProxyChangedState
)


class NSClient:
    def __init__(self, base_url: str, namespace_path: str):
        self.base_url: str = base_url
        self.namespace_path: str = namespace_path

    def __build_ns_path(self, ns_base_path: str, ns_name: str) -> str:
        return f"{ns_base_path}/{ns_name}"

    async def create_child_ns(self, relative_name: str) -> Namespace:
        """
        create_child_ns creates a new child namespace relative to this clients namespace_path.

        :param reative_name: Description
        :type reative_name: str
        :return: Return the new created namespace.
        :rtype: Namespace
        """

        to_create = Namespace(
            name=relative_name,
        )
        async with base_client(self.base_url) as client:
            ns = await namespaces_children_create.asyncio(
                self.namespace_path, client=client, body=to_create
            )
            ns = validate_response_model(ns, Namespace)
            if ns is None or ns.id is None:
                raise Exception(f"did not receive created namespace {relative_name}")
            return ns

    async def delete_ns(self, ns_name: str) -> None:
        async with base_client(self.base_url) as client:
            to_delete = self.__build_ns_path(self.namespace_path, ns_name)
            await namespaces_delete.asyncio(to_delete, client=client)

    async def get_ns_by_name(self, ns_name: str) -> Namespace | None:
        async with base_client(self.base_url) as client:
            to_get = self.__build_ns_path(self.namespace_path, ns_name)
            ns = await namespaces_get.asyncio(to_get, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    async def get_cur(self) -> Namespace | None:
        async with base_client(self.base_url) as client:
            ns = await namespaces_get.asyncio(self.namespace_path, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    # recursively retrieve all namespaces beginning with the current including all children
    async def get_all(self) -> NamespacesList200Response:
        async with base_client(self.base_url) as client:
            namespaces = await namespaces_children_list.asyncio(self.namespace_path, client=client)
            namespaces = validate_response_model(namespaces, NamespacesList200Response)
            assert namespaces
            return namespaces

    async def get_member(self, username: str) -> NsMember | None:
        async with base_client(self.base_url) as client:
            member = await members_get.asyncio(
                self.namespace_path, username=username, client=client
            )
            return validate_response_model(member, NsMember)

    async def get_members(self, role: NsRole | None = None) -> dict[NsRole, list[NsMember]]:
        async with base_client(self.base_url) as client:
            members = await members_list.asyncio(self.namespace_path, role=role, client=client)
            members = validate_response_model(members, MembersList200Response)
            assert members

            map = {}
            if members.data:
                for m in members.data:
                    l = map.get(m.role, [])
                    l.append(m)
                    map[m.role] = l
            return map

    async def get_role_members(self, role: NsRole) -> list[NsMember]:
        rm = await self.get_members(role=role)
        return rm.get(role, [])

    async def add_member(self, role: str, username: str) -> None:
        async with base_client(self.base_url) as client:
            to_create = NsMember(
                username=username,
                email="",
                first_name="",
                last_name="",
                role=NsRole(role),
            )
            member = await members_modify.asyncio(
                self.namespace_path, username, body=to_create, client=client
            )
            validate_response_model(member, NsMember)

    async def delete_member(self, username: str) -> None:
        async with base_client(self.base_url) as client:
            await members_delete.asyncio(self.namespace_path, username, client=client)


class SimBricksClient:

    def __init__(self, ns_client: NSClient) -> None:
        self._ns_client: NSClient = ns_client

    async def create_system(self, system: OrchSystem) -> ApiSystem:

        sys_sb_json = json.dumps(system.toJSON())
        to_create = ApiSystem(sb_json=sys_sb_json)

        async with base_client(self._ns_client.base_url) as client:
            sys = await systems_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            sys = validate_response_model(sys, ApiSystem)
            if sys is None or sys.id is None:
                raise Exception("did not receive cerated system")
            return sys

    async def delete_system(self, sys_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await systems_delete.asyncio(self._ns_client.namespace_path, sys_id, client=client)

    async def get_systems(self) -> SystemsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            systems = await systems_list.asyncio(self._ns_client.namespace_path, client=client)
            systems = validate_response_model(systems, SystemsList200Response)
            assert systems
            return systems

    async def get_system(self, sys_id: str) -> ApiSystem | None:
        async with base_client(self._ns_client.base_url) as client:
            sys = await systems_get.asyncio(self._ns_client.namespace_path, sys_id, client=client)
            sys = validate_response_model(sys, ApiSystem)
            return sys

    async def create_simulation(self, system_id: str, simulation: OrchSimulation) -> ApiSimulation:

        sim_sb_json = json.dumps(simulation.toJSON())
        to_create = ApiSimulation(system_id=system_id, sb_json=sim_sb_json)

        async with base_client(self._ns_client.base_url) as client:
            sim = await simulations_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            sim = validate_response_model(sim, ApiSimulation)
            if sim is None or sim.id is None:
                raise Exception("did not receive created simulation")
            return sim

    async def delete_simulation(self, sim_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await simulations_delete.asyncio(self._ns_client.namespace_path, sim_id, client=client)

    async def get_simulation(self, sim_id: str) -> ApiSimulation | None:
        async with base_client(self._ns_client.base_url) as client:
            sim = await simulations_get.asyncio(
                self._ns_client.namespace_path, sim_id, client=client
            )
            sim = validate_response_model(sim, ApiSimulation)
            return sim

    async def get_simulations(self) -> SimulationsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            sims = await simulations_list.asyncio(self._ns_client.namespace_path, client=client)
            sims = validate_response_model(sims, SimulationsList200Response)
            assert sims
            return sims

    async def create_instantiation(self, sim_id: str, inst: OrchInstantiation) -> ApiInstantiation:

        inst_sb_json = json.dumps(inst.toJSON())
        api_fragments = []
        for frag in inst.fragments:
            api_frag = ApiFragment(
                object_id=frag.id(),
                cores_required=frag.cores_required,
                memory_required=frag.memory_required,
                runner_tags=list(frag.runner_tags),
                fragment_executor_tag=None,
            )
            api_fragments.append(api_frag)
        to_create = ApiInstantiation(
            simulation_id=sim_id, sb_json=inst_sb_json, fragments=api_fragments
        )

        async with base_client(self._ns_client.base_url) as client:
            created = await instantiations_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            created = validate_response_model(created, ApiInstantiation)
            if created is None or created.id is None:
                raise Exception("did not receive created instantiation")
            return created

    async def delete_instantiation(self, inst_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await instantiations_delete.asyncio(
                self._ns_client.namespace_path, inst_id, client=client
            )

    async def get_instantiation(self, inst_id: str) -> ApiInstantiation | None:
        async with base_client(self._ns_client.base_url) as client:
            inst = await instantiations_get.asyncio(
                self._ns_client.namespace_path, inst_id, client=client
            )
            return validate_response_model(inst, ApiInstantiation)

    async def get_instantiations(self) -> InstantitionsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            insts = await instantitions_list.asyncio(self._ns_client.namespace_path, client=client)
            insts = validate_response_model(insts, InstantitionsList200Response)
            assert insts
            return insts

    async def create_run(self, inst_id: str) -> Run:

        to_create = Run(instantiation_id=inst_id, state=RunState.SPAWNED)

        async with base_client(self._ns_client.base_url) as client:
            run = await runs_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            run = validate_response_model(run, Run)
            if run is None or run.id is None:
                raise Exception("did not receive created run")
            return run

    async def delete_run(self, rid: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await runs_delete.asyncio(self._ns_client.namespace_path, rid, client=client)

    async def update_run(
        self,
        rid: str,
        instantiation_id: int | None = None,
        state: RunState | None = None,
        output: str | None = None,
    ) -> Run:

        update = Run(instantiation_id=instantiation_id, state=state, output=output)

        async with base_client(self._ns_client.base_url) as client:
            run = await runs_set.asyncio(
                self._ns_client.namespace_path, rid, client=client, body=update
            )
            run = validate_response_model(run, Run)
            if run is None:
                raise Exception("did not receive updated run")
            return run

    async def get_run(self, rid: str) -> Run | None:
        async with base_client(self._ns_client.base_url) as client:
            run = await runs_get.asyncio(self._ns_client.namespace_path, rid, client=client)
            run = validate_response_model(run, Run)
            return run

    async def get_runs(self) -> RunsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            runs = await runs_list.asyncio(self._ns_client.namespace_path, client=client)
            runs = validate_response_model(runs, RunsList200Response)
            assert runs
            return runs

    async def kill_run(self, run_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await runs_kill.asyncio(self._ns_client.namespace_path, run_id, client=client)

    async def sigusr1_run(self, run_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await runs_sigusr1.asyncio(self._ns_client.namespace_path, run_id, client=client)

    async def set_inst_input_artifact(self, inst_id: str, path_to_file: str) -> None:

        filepath = Path(path_to_file)
        assert filepath.exists() and filepath.is_file()
        with open(filepath, "rb") as fd:
            artifact_file = File(payload=fd, file_name=fd.name, mime_type="multipart/form-data")
            artifact = BodyInstantiationsInputArtifactSet(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                await instantiations_input_artifact_set.asyncio(
                    self._ns_client.namespace_path,
                    inst_id,
                    client=client,
                    body=artifact,
                )

    async def get_inst_input_artifact(self, inst_id: str, store_path: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await instantiations_input_artifact_get.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_inst_input_artifact_raw(self, inst_id: str) -> bytes:
        async with base_client(self._ns_client.base_url) as client:
            response = await instantiations_input_artifact_get.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, client=client
            )
            return response.content

    async def set_fragment_input_artifact(
        self, inst_id: str, frag_id: str, path_to_file: str
    ) -> None:
        filepath = Path(path_to_file)
        assert filepath.exists() and filepath.is_file()
        with open(filepath, "rb") as fd:
            artifact_file = File(payload=fd, file_name=fd.name, mime_type="multipart/form-data")
            artifact = BodyInstantiationsFragmentInputArtifactSet(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                resp = await instantiations_fragment_input_artifact_set.asyncio(
                    self._ns_client.namespace_path, inst_id, frag_id, client=client, body=artifact
                )

    async def get_fragment_input_artifact(
        self, inst_id: str, frag_id: str, store_path: str
    ) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await instantiations_fragment_input_artifact_get.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, frag_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_fragment_input_artifact_raw(self, inst_id: str, frag_id: str) -> bytes:
        async with base_client(self._ns_client.base_url) as client:
            response = await instantiations_fragment_input_artifact_get.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, frag_id, client=client
            )
            return response.content

    async def set_run_fragment_output_artifact(
        self, run_id: str, run_frag_id: str, path_to_file: str
    ) -> None:

        filepath = Path(path_to_file)
        assert filepath.exists() and filepath.is_file()
        with filepath.open("rb") as fd:
            artifact_file = File(payload=fd, file_name=fd.name, mime_type="multipart/form-data")
            artifact = BodyRunsFragmentsOutputArtifactSet(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                await runs_fragments_output_artifact_set.asyncio(
                    self._ns_client.namespace_path,
                    run_id,
                    run_frag_id,
                    client=client,
                    body=artifact,
                )

    async def set_run_fragment_output_artifact_raw(
        self, run_id: str, run_frag_id: int, uploaded_data: typing.IO[bytes]
    ) -> None:

        file = File(payload=uploaded_data)

        async with base_client(self._ns_client.base_url) as client:
            await runs_fragments_output_artifact_set.asyncio(
                self._ns_client.namespace_path,
                run_id,
                run_frag_id,
                client=client,
                body=BodyRunsFragmentsOutputArtifactSet(file=file),
            )

    async def get_run_fragment_output_artifact(
        self, run_id: str, frag_id: str, store_path: str
    ) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await runs_fragments_output_artifact_get.asyncio_detailed(
                self._ns_client.namespace_path, run_id, frag_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_all_run_fragments(self, run_id: str) -> RunsFragmentsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            fragments = await runs_fragments_list.asyncio(
                self._ns_client.namespace_path, run_id, client=client
            )
            fragments = validate_response_model(fragments, RunsFragmentsList200Response)
            assert fragments
            return fragments

    async def get_run_console(
        self,
        run_id: str,
        cursor_next: datetime | None = None,
        cursor_prev: datetime | None = None,
        limit: int | None = None,
        wait: int | None = None,
    ) -> RunsConsoleList200Response:
        async with base_client(self._ns_client.base_url) as client:
            console = await runs_console_list.asyncio(
                self._ns_client.namespace_path,
                run_id,
                client=client,
                cursor_next=cursor_next.isoformat() if cursor_next is not None else None,
                cursor_prev=cursor_prev.isoformat() if cursor_prev is not None else None,
                limit=limit,
                wait=wait,
            )
            console = validate_response_model(console, RunsConsoleList200Response)
            assert console
            return console


class ResourceGroupClient:

    def __init__(self, ns_client: NSClient) -> None:
        self._ns_client: NSClient = ns_client

    async def create_rg(
        self, label: str, available_cores: int, available_memory: int
    ) -> ResourceGroup:

        to_create = ResourceGroup(
            label=label,
            available_cores=available_cores,
            available_memory=available_memory,
        )

        async with base_client(self._ns_client.base_url) as client:
            rg = await resource_groups_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            rg = validate_response_model(rg, ResourceGroup)
            if rg is None or rg.id is None:
                raise Exception("did not receive created resource group")
            return rg

    async def update_rg(
        self,
        rg_id: str,
        label: str | None = None,
        available_cores: int | None = None,
        available_memory: int | None = None,
        cores_left: int | None = None,
        memory_left: int | None = None,
    ) -> ResourceGroup:

        update = ResourceGroup(
            label=label,
            available_cores=available_cores,
            available_memory=available_memory,
            cores_left=cores_left,
            memory_left=memory_left,
        )

        async with base_client(self._ns_client.base_url) as client:
            rg = await resource_groups_set.asyncio(
                self._ns_client.namespace_path, rg_id, client=client, body=update
            )
            rg = validate_response_model(rg, ResourceGroup)
            if rg is None:
                raise Exception("did not receive updated resource group")
            return rg

    async def get_rg(self, rg_id: str) -> ResourceGroup | None:
        async with base_client(self._ns_client.base_url) as client:
            rg = await resource_groups_get.asyncio(
                self._ns_client.namespace_path, rg_id, client=client
            )
            rg = validate_response_model(rg, ResourceGroup)
            return rg

    async def get_all_rg(self) -> ResourceGroupsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            rgs = await resource_groups_list.asyncio(self._ns_client.namespace_path, client=client)
            rgs = validate_response_model(rgs, ResourceGroupsList200Response)
            assert rgs
            return rgs


class RunnerClient:

    def __init__(self, ns_client: NSClient, id: str) -> None:
        self._ns_client: NSClient = ns_client
        self.runner_id = id

    async def create_runner(self, rg_id: str, label: str, tags: list[str]) -> Runner:

        tags = list(map(lambda t: RunnerTag(t), tags))
        to_create = Runner(
            resource_group_id=rg_id,
            label=label,
            tags=tags,
        )

        async with base_client(self._ns_client.base_url) as client:
            runner = await runners_create.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            runner = validate_response_model(runner, Runner)
            if runner is None or runner.id is None:
                raise Exception("did not receive created runner")
            return runner

    async def delete_runner(self) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await runners_delete.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client
            )

    async def get_runner(self) -> Runner | None:
        async with base_client(self._ns_client.base_url) as client:
            runner = await runners_get.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client
            )
            runner = validate_response_model(runner, Runner)
            return runner

    async def list_runners(self) -> RunnersList200Response:
        async with base_client(self._ns_client.base_url) as client:
            runners = await runners_list.asyncio(self._ns_client.namespace_path, client=client)
            runners = validate_response_model(runners, RunnersList200Response)
            assert runners
            return runners

    async def submit_event(self, event: EventFromRunner_U) -> RunnersFromEventsList200Response:
        return await self.submit_events([event])

    async def submit_events(
        self, events: list[EventFromRunner_U]
    ) -> RunnersFromEventsList200Response:

        request_body = RunnersFromEventsCreateRequest(data=events)

        async with base_client(self._ns_client.base_url) as client:
            submitted_events = await runners_from_events_create.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client, body=request_body
            )
            submitted_events = validate_response_model(
                submitted_events, RunnersFromEventsList200Response
            )
            assert submitted_events
            return submitted_events

    async def retrieve_events(
        self,
        cursor_next: str | None = None,
        cursor_prev: str | None = None,
        limit: int | None = None,
        deleted: bool | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> RunnersToEventsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            events = await runners_to_events_list.asyncio(
                self._ns_client.namespace_path,
                self.runner_id,
                client=client,
                cursor_next=cursor_next,
                cursor_prev=cursor_prev,
                limit=limit,
                deleted=deleted,
                after=after,
                before=before,
            )
            events = validate_response_model(events, RunnersToEventsList200Response)
            assert events
            return events

    async def delete_retrieved_events_until_event(self, event_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await runners_to_events_delete.asyncio(
                self._ns_client.namespace_path,
                self.runner_id,
                event_id,
                client=client,
            )


async def resolve_default_ns(base_url: str) -> str:
    async with base_client(base_url) as client:
        membership = await user_default_membership.asyncio(client=client)
        membership = validate_response_model(membership, NsMember)
        namespace_path = membership.namespace_full_path
        assert namespace_path
        return namespace_path


async def ns_client(
    base_url: str | None = None,
    namespace_path: str | None = None,
) -> NSClient:
    if base_url is None:
        base_url = client_settings().base_url

    namespace_path = namespace_path if namespace_path is not None else client_settings().namespace
    if namespace_path is None:
        namespace_path = await resolve_default_ns(base_url)

    return NSClient(base_url, namespace_path)


async def simb_client(nsc: NSClient | None = None) -> SimBricksClient:
    if nsc is None:
        nsc = await ns_client()

    return SimBricksClient(nsc)


async def rg_client(nsc: NSClient | None = None) -> ResourceGroupClient:
    if nsc is None:
        nsc = await ns_client()

    return ResourceGroupClient(nsc)


async def runner_client(runner_id: str, nsc: NSClient | None = None) -> RunnerClient:
    if nsc is None:
        nsc = await ns_client()

    return RunnerClient(nsc, runner_id)

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
from simbricks.client.openapi.client.sim_bricks_api_client.api.namespace_base import (
    resolve_default_user_namspace_name_resolve_default_user_get_resolve_default_user_get as resolve_default_ns,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.members import (
    members_delete_ns_ns_path_members_username_delete as members_delete_ns,
    members_get_ns_ns_path_members_username_get as members_get_ns,
    members_list_ns_ns_path_members_get as members_list_ns,
    members_modify_ns_ns_path_members_username_put as members_update_ns,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.namespaces import (
    namespaces_children_create_ns_ns_path_children_post as create_child_ns,
    namespaces_children_list_ns_ns_path_children_get as list_child_ns,
    namespaces_get_ns_ns_path_get as ns_by_path,
    namespaces_delete_ns_ns_path_delete as delete_ns_by_path,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.systems import (
    systems_create_ns_ns_path_systems_post as create_sys,
    systems_get_ns_ns_path_systems_sys_id_get as get_sys,
    systems_list_ns_ns_path_systems_get as list_sys,
    systems_delete_ns_ns_path_systems_sys_id_delete as delete_sys,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.simulations import (
    simulations_create_ns_ns_path_simulations_post as create_sim,
    simulations_get_ns_ns_path_simulations_sim_id_get as get_sim,
    simulations_list_ns_ns_path_simulations_get as list_sim,
    simulations_delete_ns_ns_path_simulations_sim_id_delete as delete_sim,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.instantiations import (
    instantiations_create_ns_ns_path_instantiations_post as create_inst,
    instantiations_get_ns_ns_path_instantiations_inst_id_get as get_inst,
    instantitions_list_ns_ns_path_instantiations_get as list_inst,
    instantiations_delete_ns_ns_path_instantiations_inst_id_delete as delete_inst,
    instantiations_fragments_list_ns_ns_path_instantiations_inst_id_fragments_get as inst_fragments_get,
    instantiations_input_artifact_set_ns_ns_path_instantiations_inst_id_input_artifact_put as inst_set_input_artifact,
    instantiations_input_artifact_get_ns_ns_path_instantiations_inst_id_input_artifact_get as inst_get_input_artifact,
    instantiations_fragment_input_artifact_set_ns_ns_path_instantiations_inst_id_fragments_frag_id_input_artifact_put as inst_set_fragment_input_artifact,
    instantiations_fragment_input_artifact_get_ns_ns_path_instantiations_inst_id_fragments_frag_id_input_artifact_get as inst_get_fragment_input_artifact,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.runs import (
    runs_create_ns_ns_path_runs_post as create_run,
    runs_set_ns_ns_path_runs_run_id_patch as update_run,
    runs_list_ns_ns_path_runs_get as list_runs,
    runs_delete_ns_ns_path_runs_run_id_delete as delete_run,
    runs_get_ns_ns_path_runs_run_id_get as get_run_by_id,
    runs_console_list_ns_ns_path_runs_run_id_console_get as get_run_console,
    runs_fragments_output_artifact_set_ns_ns_path_runs_run_id_fragments_frag_id_output_artifacts_put as set_run_frag_out_artifact,
    runs_fragments_output_artifact_get_ns_ns_path_runs_run_id_fragments_frag_id_output_artifacts_get as get_run_frag_out_artifact,
    runs_fragments_list_ns_ns_path_runs_run_id_fragments_get as list_run_frags,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.resource_groups import (
    resource_groups_create_ns_ns_path_resource_groups_post as create_rg,
    resource_groups_get_ns_ns_path_resource_group_rg_id_get as get_rg,
    resource_groups_list_ns_ns_path_resource_groups_get as list_rg,
    resource_groups_set_ns_ns_path_resource_group_rg_id_put as update_rg,
)
from simbricks.client.openapi.client.sim_bricks_api_client.api.runners import (
    runners_create_ns_ns_path_runners_post as create_runner,
    runners_delete_ns_ns_path_runners_runner_id_delete as delete_runner,
    runners_get_ns_ns_path_runners_runner_id_get as get_runner,
    runners_list_ns_ns_path_runners_get as list_runner,
    runners_from_events_create_ns_ns_path_runners_runner_id_events_from_runner_post as create_events_from_runner,
    runners_to_events_list_ns_ns_path_runners_runner_id_events_to_runner_get as get_events_to_runner,
    runners_to_events_delete_ns_ns_path_runners_runner_id_events_to_runner_event_id_delete as delete_events_to_runner,
)
from simbricks.client.openapi.client.sim_bricks_api_client.models import (
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
    BodyInstantiationsInputArtifactSetNsNsPathInstantiationsInstIdInputArtifactPut as InstArt,
    BodyInstantiationsFragmentInputArtifactSetNsNsPathInstantiationsInstIdFragmentsFragIdInputArtifactPut as InstFragArt,
    BodyRunsFragmentsOutputArtifactSetNsNsPathRunsRunIdFragmentsFragIdOutputArtifactsPut as RunFragOutArt,
    ResourceGroup,
    ResourceGroupsList200Response,
    Runner,
    RunnersList200Response,
    RunnerStatus,
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
    RunFragment,
    RunnerStarted,
    SimulationSigusr1,
    SimulatorChangedState,
    ProxyChangedState,
)
from simbricks.client.openapi.client.sim_bricks_api_client.types import File
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
    def __init__(self, base_url: str, namespace_path: str | None = None):
        self.base_url: str = base_url
        self.namespace_path: str | None = namespace_path

    def __build_ns_path(self, ns_base_path: str, ns_name: str) -> str:
        return f"{ns_base_path}/{ns_name}"

    async def resolve_default_ns(self) -> None:
        if self.namespace_path is not None:
            return

        async with base_client(self.base_url) as client:
            ns: Namespace = await resolve_default_ns.asyncio(client=client)
            self.namespace_path = self.__build_ns_path(ns.base_path, ns.name)

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
            ns = await create_child_ns.asyncio(self.namespace_path, client=client, body=to_create)
            ns = validate_response_model(ns, Namespace)
            return ns

    async def delete_ns(self, ns_name: str) -> None:
        async with base_client(self.base_url) as client:
            to_delete = self.__build_ns_path(self.namespace_path, ns_name)
            await delete_ns_by_path.asyncio(to_delete, client=client)

    async def get_ns_by_name(self, ns_name: str) -> Namespace:
        async with base_client(self.base_url) as client:
            to_get = self.__build_ns_path(self.namespace_path, ns_name)
            ns = await ns_by_path.asyncio(to_get, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    async def get_cur(self) -> Namespace:
        async with base_client(self.base_url) as client:
            ns = await ns_by_path.asyncio(self.namespace_path, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    # recursively retrieve all namespaces beginning with the current including all children
    async def get_all(self) -> NamespacesList200Response:
        async with base_client(self.base_url) as client:
            namespaces = await list_child_ns.asyncio(self.namespace_path, client=client)
            namespaces = validate_response_model(namespaces, NamespacesList200Response)
            return namespaces

    async def get_member(self, username: str) -> NsMember:
        async with base_client(self.base_url) as client:
            member = await members_get_ns.asyncio(self.namespace_path, username=username, client=client)
            return validate_response_model(member, NsMember)

    async def get_members(self, role: NsRole | None = None) -> dict[NsRole, list[NsMember]]:
        async with base_client(self.base_url) as client:
            members = await members_list_ns.asyncio(self.namespace_path, role=role, client=client)
            members = validate_response_model(members, MembersList200Response)
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
            member = await members_update_ns.asyncio(self.namespace_path, username, body=to_create, client=client)
            validate_response_model(member, NsMember)

    async def delete_member(self, username: str) -> None:
        async with base_client(self.base_url) as client:
            await members_delete_ns.asyncio(self.namespace_path, username, client=client)



class SimBricksClient:

    def __init__(self, ns_client: NSClient) -> None:
        self._ns_client: NSClient = ns_client

    async def create_system(self, system: OrchSystem) -> ApiSystem:

        sys_sb_json = json.dumps(system.toJSON())
        to_create = ApiSystem(sb_json=sys_sb_json)

        async with base_client(self._ns_client.base_url) as client:
            sys = await create_sys.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            return sys

    async def delete_system(self, sys_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_sys.asyncio(self._ns_client.namespace_path, sys_id, client=client)

    async def get_systems(self) -> SystemsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            systems = await list_sys.asyncio(self._ns_client.namespace_path, client=client)
            systems = validate_response_model(systems, SystemsList200Response)
            return systems

    async def get_system(self, sys_id: str) -> ApiSystem:
        async with base_client(self._ns_client.base_url) as client:
            sys = await get_sys.asyncio(self._ns_client.namespace_path, sys_id, client=client)
            return sys

    async def create_simulation(self, system_id: str, simulation: OrchSimulation) -> ApiSimulation:

        sim_sb_json = json.dumps(simulation.toJSON())
        to_create = ApiSimulation(system_id=system_id, sb_json=sim_sb_json)

        async with base_client(self._ns_client.base_url) as client:
            sim = await create_sim.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            return sim

    async def delete_simulation(self, sim_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_sim.asyncio(self._ns_client.namespace_path, sim_id, client=client)

    async def get_simulation(self, sim_id: int) -> ApiSimulation:
        async with base_client(self._ns_client.base_url) as client:
            sim = await get_sim.asyncio(self._ns_client.namespace_path, sim_id, client=client)
            return sim

    async def get_simulations(self) -> SimulationsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            sims = await list_sim.asyncio(self._ns_client.namespace_path, client=client)
            sims = validate_response_model(sims, SimulationsList200Response)
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
            inst = await create_inst.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            return inst

    async def delete_instantiation(self, inst_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_inst.asyncio(self._ns_client.namespace_path, inst_id, client=client)

    async def get_instantiation(self, inst_id: str) -> ApiInstantiation:
        async with base_client(self._ns_client.base_url) as client:
            inst = await get_inst.asyncio(self._ns_client.namespace_path, inst_id, client=client)
            return inst

    async def get_instantiations(self) -> InstantitionsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            insts = await list_inst.asyncio(self._ns_client.namespace_path, client=client)
            insts = validate_response_model(insts, InstantitionsList200Response)
            return insts

    async def create_run(self, inst_id: str) -> Run:

        to_create = Run(instantiation_id=inst_id, state=RunState.SPAWNED)

        async with base_client(self._ns_client.base_url) as client:
            run = await create_run.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            return run

    async def delete_run(self, rid: int) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_run.asyncio(self._ns_client.namespace_path, rid, client=client)

    async def update_run(
        self,
        rid: str,
        instantiation_id: int | None = None,
        state: RunState | None = None,
        output: str | None = None,
    ) -> Run:

        update = Run(instantiation_id=instantiation_id, state=state, output=output)

        async with base_client(self._ns_client.base_url) as client:
            run = await update_run.asyncio(
                self._ns_client.namespace_path, rid, client=client, body=update
            )
            return run

    async def get_run(self, rid: str) -> Run:
        async with base_client(self._ns_client.base_url) as client:
            run = await get_run_by_id.asyncio(self._ns_client.namespace_path, rid, client=client)
            return run

    async def get_runs(self) -> RunsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            runs = await list_runs.asyncio(self._ns_client.namespace_path, client=client)
            runs = validate_response_model(runs, RunsList200Response)
            return runs

    async def set_inst_input_artifact(self, inst_id: str, path_to_file: str) -> None:

        filepath = Path(path_to_file)
        assert filepath.exists() and filepath.is_file()
        with open(filepath, "rb") as fd:
            artifact_file = File(payload=fd, file_name=fd.name, mime_type="multipart/form-data")
            artifact = InstArt(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                resp = await inst_set_input_artifact.asyncio(
                    self._ns_client.namespace_path,
                    inst_id,
                    client=client,
                    body=artifact,
                )

    async def get_inst_input_artifact(self, inst_id: str, store_path: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await inst_get_input_artifact.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_inst_input_artifact_raw(self, inst_id: str) -> bytes:
        async with base_client(self._ns_client.base_url) as client:
            response = await inst_get_input_artifact.asyncio_detailed(
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
            artifact = InstFragArt(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                resp = await inst_set_fragment_input_artifact.asyncio(
                    self._ns_client.namespace_path, inst_id, frag_id, client=client, body=artifact
                )

    async def get_fragment_input_artifact(
        self, inst_id: str, frag_id: str, store_path: str
    ) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await inst_get_fragment_input_artifact.asyncio_detailed(
                self._ns_client.namespace_path, inst_id, frag_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_fragment_input_artifact_raw(self, inst_id: str, frag_id: str) -> bytes:
        async with base_client(self._ns_client.base_url) as client:
            response = await inst_get_fragment_input_artifact.asyncio_detailed(
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
            artifact = RunFragOutArt(file=artifact_file)

            async with base_client(self._ns_client.base_url) as client:
                await set_run_frag_out_artifact.asyncio(
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
            await set_run_frag_out_artifact.asyncio(
                self._ns_client.namespace_path,
                run_id,
                run_frag_id,
                client=client,
                body=RunFragOutArt(file=file),
            )

    async def get_run_fragment_output_artifact(
        self, run_id: str, frag_id: str, store_path: str
    ) -> None:
        async with base_client(self._ns_client.base_url) as client:
            response = await get_run_frag_out_artifact.asyncio_detailed(
                self._ns_client.namespace_path, run_id, frag_id, client=client
            )
            with open(store_path, "wb") as fd:
                fd.write(response.content)

    async def get_all_run_fragments(self, run_id: str) -> RunsFragmentsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            fragments = await list_run_frags.asyncio(
                self._ns_client.namespace_path, run_id, client=client
            )
            fragments = validate_response_model(fragments, RunsFragmentsList200Response)
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
            console = await get_run_console.asyncio(
                self._ns_client.namespace_path,
                run_id,
                client=client,
                cursor_next=cursor_next.isoformat() if cursor_next is not None else None,
                cursor_prev=cursor_prev.isoformat() if cursor_prev is not None else None,
                limit=limit,
                wait=wait,
            )
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
            rg = await create_rg.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
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
            rg = await update_rg.asyncio(
                self._ns_client.namespace_path, rg_id, client=client, body=update
            )
            return rg

    async def get_rg(self, rg_id: str) -> ResourceGroup:
        async with base_client(self._ns_client.base_url) as client:
            rg = await get_rg.asyncio(self._ns_client.namespace_path, rg_id, client=client)
            return rg

    async def get_all_rg(self) -> ResourceGroupsList200Response:
        async with base_client(self._ns_client.base_url) as client:
            rgs = await list_rg.asyncio(self._ns_client.namespace_path, client=client)
            rgs = validate_response_model(rgs, ResourceGroupsList200Response)
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
            runner = await create_runner.asyncio(
                self._ns_client.namespace_path, client=client, body=to_create
            )
            return runner

    async def delete_runner(self) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_runner.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client
            )

    async def get_runner(self) -> Runner:
        async with base_client(self._ns_client.base_url) as client:
            runner = await get_runner.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client
            )
            return runner

    async def list_runners(self) -> RunnersList200Response:
        async with base_client(self._ns_client.base_url) as client:
            runners = await list_runner.asyncio(self._ns_client.namespace_path, client=client)
            runners = validate_response_model(runners, RunnersList200Response)
            return runners

    async def submit_event(self, event: EventFromRunner_U) -> RunnersFromEventsList200Response:
        return await self.submit_events([event])

    async def submit_events(
        self, events: list[EventFromRunner_U]
    ) -> RunnersFromEventsList200Response:

        request_body = RunnersFromEventsCreateRequest(data=events)

        async with base_client(self._ns_client.base_url) as client:
            submitted_events = await create_events_from_runner.asyncio(
                self._ns_client.namespace_path, self.runner_id, client=client, body=request_body
            )
            submitted_events = validate_response_model(
                submitted_events, RunnersFromEventsList200Response
            )
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
            events = await get_events_to_runner.asyncio(
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
            return events

    async def delete_retrieved_events_until_event(self, event_id: str) -> None:
        async with base_client(self._ns_client.base_url) as client:
            await delete_events_to_runner.asyncio(
                self._ns_client.namespace_path,
                self.runner_id,
                event_id,
                client=client,
            )


def ns_client(
    base_url: str | None = None,
    namespace_path: str | None = None,
) -> NSClient:
    return NSClient(
      base_url if base_url is not None else client_settings().base_url,
      namespace_path if namespace_path is not None else client_settings().namespace)


def simb_client(nsc: NSClient | None = None) -> SimBricksClient:
    return SimBricksClient(
      nsc if nsc is not None else ns_client())


def rg_client(nsc: NSClient | None) -> ResourceGroupClient:
    return ResourceGroupClient(
      nsc if nsc is not None else ns_client())


def runner_client(runner_id: str, nsc: NSClient | None = None) -> RunnerClient:
    return RunnerClient(
        nsc if nsc is not None else ns_client(),
        runner_id)

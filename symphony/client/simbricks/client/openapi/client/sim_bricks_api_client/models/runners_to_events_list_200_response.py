from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.kill_run_req import KillRunReq
    from ..models.pagination_links import PaginationLinks
    from ..models.proxy_changed_state import ProxyChangedState
    from ..models.runner_heartbeat_req import RunnerHeartbeatReq
    from ..models.simulation_sigusr_1 import SimulationSigusr1
    from ..models.simulator_changed_state import SimulatorChangedState
    from ..models.start_run_req import StartRunReq


T = TypeVar("T", bound="RunnersToEventsList200Response")


@_attrs_define
class RunnersToEventsList200Response:
    """RunnersToEventsList200Response

    Attributes:
        data (list[KillRunReq | ProxyChangedState | RunnerHeartbeatReq | SimulationSigusr1 | SimulatorChangedState |
            StartRunReq] | None | Unset):
        links (None | PaginationLinks | Unset):
    """

    data: (
        list[
            KillRunReq
            | ProxyChangedState
            | RunnerHeartbeatReq
            | SimulationSigusr1
            | SimulatorChangedState
            | StartRunReq
        ]
        | None
        | Unset
    ) = UNSET
    links: None | PaginationLinks | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.kill_run_req import KillRunReq
        from ..models.pagination_links import PaginationLinks
        from ..models.runner_heartbeat_req import RunnerHeartbeatReq
        from ..models.simulation_sigusr_1 import SimulationSigusr1
        from ..models.simulator_changed_state import SimulatorChangedState
        from ..models.start_run_req import StartRunReq

        data: list[dict[str, Any]] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, list):
            data = []
            for data_type_0_item_data in self.data:
                data_type_0_item: dict[str, Any]
                if isinstance(data_type_0_item_data, RunnerHeartbeatReq):
                    data_type_0_item = data_type_0_item_data.to_dict()
                elif isinstance(data_type_0_item_data, StartRunReq):
                    data_type_0_item = data_type_0_item_data.to_dict()
                elif isinstance(data_type_0_item_data, KillRunReq):
                    data_type_0_item = data_type_0_item_data.to_dict()
                elif isinstance(data_type_0_item_data, SimulationSigusr1):
                    data_type_0_item = data_type_0_item_data.to_dict()
                elif isinstance(data_type_0_item_data, SimulatorChangedState):
                    data_type_0_item = data_type_0_item_data.to_dict()
                else:
                    data_type_0_item = data_type_0_item_data.to_dict()

                data.append(data_type_0_item)

        else:
            data = self.data

        links: dict[str, Any] | None | Unset
        if isinstance(self.links, Unset):
            links = UNSET
        elif isinstance(self.links, PaginationLinks):
            links = self.links.to_dict()
        else:
            links = self.links

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data
        if links is not UNSET:
            field_dict["links"] = links

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.kill_run_req import KillRunReq
        from ..models.pagination_links import PaginationLinks
        from ..models.proxy_changed_state import ProxyChangedState
        from ..models.runner_heartbeat_req import RunnerHeartbeatReq
        from ..models.simulation_sigusr_1 import SimulationSigusr1
        from ..models.simulator_changed_state import SimulatorChangedState
        from ..models.start_run_req import StartRunReq

        d = dict(src_dict)

        def _parse_data(
            data: object,
        ) -> (
            list[
                KillRunReq
                | ProxyChangedState
                | RunnerHeartbeatReq
                | SimulationSigusr1
                | SimulatorChangedState
                | StartRunReq
            ]
            | None
            | Unset
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                data_type_0 = []
                _data_type_0 = data
                for data_type_0_item_data in _data_type_0:

                    def _parse_data_type_0_item(
                        data: object,
                    ) -> (
                        KillRunReq
                        | ProxyChangedState
                        | RunnerHeartbeatReq
                        | SimulationSigusr1
                        | SimulatorChangedState
                        | StartRunReq
                    ):
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            data_type_0_item_type_0 = RunnerHeartbeatReq.from_dict(data)

                            return data_type_0_item_type_0
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            data_type_0_item_type_1 = StartRunReq.from_dict(data)

                            return data_type_0_item_type_1
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            data_type_0_item_type_2 = KillRunReq.from_dict(data)

                            return data_type_0_item_type_2
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            data_type_0_item_type_3 = SimulationSigusr1.from_dict(data)

                            return data_type_0_item_type_3
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        try:
                            if not isinstance(data, dict):
                                raise TypeError()
                            data_type_0_item_type_4 = SimulatorChangedState.from_dict(data)

                            return data_type_0_item_type_4
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_type_0_item_type_5 = ProxyChangedState.from_dict(data)

                        return data_type_0_item_type_5

                    data_type_0_item = _parse_data_type_0_item(data_type_0_item_data)

                    data_type_0.append(data_type_0_item)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                list[
                    KillRunReq
                    | ProxyChangedState
                    | RunnerHeartbeatReq
                    | SimulationSigusr1
                    | SimulatorChangedState
                    | StartRunReq
                ]
                | None
                | Unset,
                data,
            )

        data = _parse_data(d.pop("data", UNSET))

        def _parse_links(data: object) -> None | PaginationLinks | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                links_type_0 = PaginationLinks.from_dict(data)

                return links_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | PaginationLinks | Unset, data)

        links = _parse_links(d.pop("links", UNSET))

        runners_to_events_list_200_response = cls(
            data=data,
            links=links,
        )

        runners_to_events_list_200_response.additional_properties = d
        return runners_to_events_list_200_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties

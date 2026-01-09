from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.fragment_output_artifact import FragmentOutputArtifact
    from ..models.fragment_state_change import FragmentStateChange
    from ..models.pagination_links import PaginationLinks
    from ..models.proxy_output import ProxyOutput
    from ..models.proxy_state_change import ProxyStateChange
    from ..models.run_status import RunStatus
    from ..models.runner_heartbeat import RunnerHeartbeat
    from ..models.runner_started import RunnerStarted
    from ..models.simulator_output import SimulatorOutput
    from ..models.simulator_state_change import SimulatorStateChange


T = TypeVar("T", bound="RunnersFromEventsList200Response")


@_attrs_define
class RunnersFromEventsList200Response:
    """RunnersFromEventsList200Response

    Attributes:
        data (list[FragmentOutputArtifact | FragmentStateChange | ProxyOutput | ProxyStateChange | RunnerHeartbeat |
            RunnerStarted | RunStatus | SimulatorOutput | SimulatorStateChange] | Unset):
        links (None | PaginationLinks | Unset):
    """

    data: (
        list[
            FragmentOutputArtifact
            | FragmentStateChange
            | ProxyOutput
            | ProxyStateChange
            | RunnerHeartbeat
            | RunnerStarted
            | RunStatus
            | SimulatorOutput
            | SimulatorStateChange
        ]
        | Unset
    ) = UNSET
    links: None | PaginationLinks | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.fragment_state_change import FragmentStateChange
        from ..models.pagination_links import PaginationLinks
        from ..models.proxy_output import ProxyOutput
        from ..models.proxy_state_change import ProxyStateChange
        from ..models.run_status import RunStatus
        from ..models.runner_heartbeat import RunnerHeartbeat
        from ..models.runner_started import RunnerStarted
        from ..models.simulator_output import SimulatorOutput
        from ..models.simulator_state_change import SimulatorStateChange

        data: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = []
            for data_item_data in self.data:
                data_item: dict[str, Any]
                if isinstance(data_item_data, RunnerStarted):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, RunnerHeartbeat):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, RunStatus):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, SimulatorOutput):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, SimulatorStateChange):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, ProxyOutput):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, ProxyStateChange):
                    data_item = data_item_data.to_dict()
                elif isinstance(data_item_data, FragmentStateChange):
                    data_item = data_item_data.to_dict()
                else:
                    data_item = data_item_data.to_dict()

                data.append(data_item)

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
        from ..models.fragment_output_artifact import FragmentOutputArtifact
        from ..models.fragment_state_change import FragmentStateChange
        from ..models.pagination_links import PaginationLinks
        from ..models.proxy_output import ProxyOutput
        from ..models.proxy_state_change import ProxyStateChange
        from ..models.run_status import RunStatus
        from ..models.runner_heartbeat import RunnerHeartbeat
        from ..models.runner_started import RunnerStarted
        from ..models.simulator_output import SimulatorOutput
        from ..models.simulator_state_change import SimulatorStateChange

        d = dict(src_dict)
        _data = d.pop("data", UNSET)
        data: (
            list[
                FragmentOutputArtifact
                | FragmentStateChange
                | ProxyOutput
                | ProxyStateChange
                | RunnerHeartbeat
                | RunnerStarted
                | RunStatus
                | SimulatorOutput
                | SimulatorStateChange
            ]
            | Unset
        ) = UNSET
        if _data is not UNSET:
            data = []
            for data_item_data in _data:

                def _parse_data_item(
                    data: object,
                ) -> (
                    FragmentOutputArtifact
                    | FragmentStateChange
                    | ProxyOutput
                    | ProxyStateChange
                    | RunnerHeartbeat
                    | RunnerStarted
                    | RunStatus
                    | SimulatorOutput
                    | SimulatorStateChange
                ):
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_0 = RunnerStarted.from_dict(data)

                        return data_item_type_0
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_1 = RunnerHeartbeat.from_dict(data)

                        return data_item_type_1
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_2 = RunStatus.from_dict(data)

                        return data_item_type_2
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_3 = SimulatorOutput.from_dict(data)

                        return data_item_type_3
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_4 = SimulatorStateChange.from_dict(data)

                        return data_item_type_4
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_5 = ProxyOutput.from_dict(data)

                        return data_item_type_5
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_6 = ProxyStateChange.from_dict(data)

                        return data_item_type_6
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    try:
                        if not isinstance(data, dict):
                            raise TypeError()
                        data_item_type_7 = FragmentStateChange.from_dict(data)

                        return data_item_type_7
                    except (TypeError, ValueError, AttributeError, KeyError):
                        pass
                    if not isinstance(data, dict):
                        raise TypeError()
                    data_item_type_8 = FragmentOutputArtifact.from_dict(data)

                    return data_item_type_8

                data_item = _parse_data_item(data_item_data)

                data.append(data_item)

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

        runners_from_events_list_200_response = cls(
            data=data,
            links=links,
        )

        runners_from_events_list_200_response.additional_properties = d
        return runners_from_events_list_200_response

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

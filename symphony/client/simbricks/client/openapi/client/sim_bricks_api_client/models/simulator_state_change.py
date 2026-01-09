from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.run_component_state import RunComponentState
from ..types import UNSET, Unset

T = TypeVar("T", bound="SimulatorStateChange")


@_attrs_define
class SimulatorStateChange:
    """
    Attributes:
        simulator_id (int):
        run_id (int):
        simulator_state (RunComponentState):
        id (None | str | Unset): API Object id
        produced_at (datetime.datetime | Unset):
        simulator_name (None | str | Unset):
        command (None | str | Unset):
    """

    simulator_id: int
    run_id: int
    simulator_state: RunComponentState
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    simulator_name: None | str | Unset = UNSET
    command: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        simulator_id = self.simulator_id

        run_id = self.run_id

        simulator_state = self.simulator_state.value

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        produced_at: str | Unset = UNSET
        if not isinstance(self.produced_at, Unset):
            produced_at = self.produced_at.isoformat()

        simulator_name: None | str | Unset
        if isinstance(self.simulator_name, Unset):
            simulator_name = UNSET
        else:
            simulator_name = self.simulator_name

        command: None | str | Unset
        if isinstance(self.command, Unset):
            command = UNSET
        else:
            command = self.command

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "simulator_id": simulator_id,
                "run_id": run_id,
                "simulator_state": simulator_state,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if produced_at is not UNSET:
            field_dict["produced_at"] = produced_at
        if simulator_name is not UNSET:
            field_dict["simulator_name"] = simulator_name
        if command is not UNSET:
            field_dict["command"] = command

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        simulator_id = d.pop("simulator_id")

        run_id = d.pop("run_id")

        simulator_state = RunComponentState(d.pop("simulator_state"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        _produced_at = d.pop("produced_at", UNSET)
        produced_at: datetime.datetime | Unset
        if isinstance(_produced_at, Unset):
            produced_at = UNSET
        else:
            produced_at = isoparse(_produced_at)

        def _parse_simulator_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        simulator_name = _parse_simulator_name(d.pop("simulator_name", UNSET))

        def _parse_command(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        command = _parse_command(d.pop("command", UNSET))

        simulator_state_change = cls(
            simulator_id=simulator_id,
            run_id=run_id,
            simulator_state=simulator_state,
            id=id,
            produced_at=produced_at,
            simulator_name=simulator_name,
            command=command,
        )

        simulator_state_change.additional_properties = d
        return simulator_state_change

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

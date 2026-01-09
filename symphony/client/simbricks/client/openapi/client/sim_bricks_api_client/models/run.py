from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.run_state import RunState
from ..types import UNSET, Unset

T = TypeVar("T", bound="Run")


@_attrs_define
class Run:
    """Run

    Attributes:
        id (None | str | Unset): API Object id
        namespace_id (None | str | Unset): API Object id
        instantiation_id (None | str | Unset): API Object id
        output (None | str | Unset):
        state (None | RunState | Unset):
    """

    id: None | str | Unset = UNSET
    namespace_id: None | str | Unset = UNSET
    instantiation_id: None | str | Unset = UNSET
    output: None | str | Unset = UNSET
    state: None | RunState | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        namespace_id: None | str | Unset
        if isinstance(self.namespace_id, Unset):
            namespace_id = UNSET
        else:
            namespace_id = self.namespace_id

        instantiation_id: None | str | Unset
        if isinstance(self.instantiation_id, Unset):
            instantiation_id = UNSET
        else:
            instantiation_id = self.instantiation_id

        output: None | str | Unset
        if isinstance(self.output, Unset):
            output = UNSET
        else:
            output = self.output

        state: None | str | Unset
        if isinstance(self.state, Unset):
            state = UNSET
        elif isinstance(self.state, RunState):
            state = self.state.value
        else:
            state = self.state

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if namespace_id is not UNSET:
            field_dict["namespace_id"] = namespace_id
        if instantiation_id is not UNSET:
            field_dict["instantiation_id"] = instantiation_id
        if output is not UNSET:
            field_dict["output"] = output
        if state is not UNSET:
            field_dict["state"] = state

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_namespace_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        namespace_id = _parse_namespace_id(d.pop("namespace_id", UNSET))

        def _parse_instantiation_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        instantiation_id = _parse_instantiation_id(d.pop("instantiation_id", UNSET))

        def _parse_output(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        output = _parse_output(d.pop("output", UNSET))

        def _parse_state(data: object) -> None | RunState | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                state_type_0 = RunState(data)

                return state_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunState | Unset, data)

        state = _parse_state(d.pop("state", UNSET))

        run = cls(
            id=id,
            namespace_id=namespace_id,
            instantiation_id=instantiation_id,
            output=output,
            state=state,
        )

        run.additional_properties = d
        return run

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

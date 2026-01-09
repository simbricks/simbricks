from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.run_state import RunState
from ..types import UNSET, Unset

T = TypeVar("T", bound="RunFragment")


@_attrs_define
class RunFragment:
    """RunFragment

    Attributes:
        run_id (None | str | Unset): API Object id
        fragment_id (None | str | Unset): API Object id
        runner_id (None | str | Unset): API Object id
        output_artifact_exists (bool | None | Unset):
        state (None | RunState | Unset):
    """

    run_id: None | str | Unset = UNSET
    fragment_id: None | str | Unset = UNSET
    runner_id: None | str | Unset = UNSET
    output_artifact_exists: bool | None | Unset = UNSET
    state: None | RunState | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        run_id: None | str | Unset
        if isinstance(self.run_id, Unset):
            run_id = UNSET
        else:
            run_id = self.run_id

        fragment_id: None | str | Unset
        if isinstance(self.fragment_id, Unset):
            fragment_id = UNSET
        else:
            fragment_id = self.fragment_id

        runner_id: None | str | Unset
        if isinstance(self.runner_id, Unset):
            runner_id = UNSET
        else:
            runner_id = self.runner_id

        output_artifact_exists: bool | None | Unset
        if isinstance(self.output_artifact_exists, Unset):
            output_artifact_exists = UNSET
        else:
            output_artifact_exists = self.output_artifact_exists

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
        if run_id is not UNSET:
            field_dict["run_id"] = run_id
        if fragment_id is not UNSET:
            field_dict["fragment_id"] = fragment_id
        if runner_id is not UNSET:
            field_dict["runner_id"] = runner_id
        if output_artifact_exists is not UNSET:
            field_dict["output_artifact_exists"] = output_artifact_exists
        if state is not UNSET:
            field_dict["state"] = state

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_run_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        run_id = _parse_run_id(d.pop("run_id", UNSET))

        def _parse_fragment_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        fragment_id = _parse_fragment_id(d.pop("fragment_id", UNSET))

        def _parse_runner_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        runner_id = _parse_runner_id(d.pop("runner_id", UNSET))

        def _parse_output_artifact_exists(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        output_artifact_exists = _parse_output_artifact_exists(d.pop("output_artifact_exists", UNSET))

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

        run_fragment = cls(
            run_id=run_id,
            fragment_id=fragment_id,
            runner_id=runner_id,
            output_artifact_exists=output_artifact_exists,
            state=state,
        )

        run_fragment.additional_properties = d
        return run_fragment

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

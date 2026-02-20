from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="ConsoleOutputLine")


@_attrs_define
class ConsoleOutputLine:
    """ConsoleOutputLine

    Attributes:
        is_stderr (bool):
        output (str):
        produced_at (datetime.datetime):
        id (None | str | Unset): API Object id
    """

    is_stderr: bool
    output: str
    produced_at: datetime.datetime
    id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        is_stderr = self.is_stderr

        output = self.output

        produced_at = self.produced_at.isoformat()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "is_stderr": is_stderr,
                "output": output,
                "produced_at": produced_at,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        is_stderr = d.pop("is_stderr")

        output = d.pop("output")

        produced_at = isoparse(d.pop("produced_at"))

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        console_output_line = cls(
            is_stderr=is_stderr,
            output=output,
            produced_at=produced_at,
            id=id,
        )

        console_output_line.additional_properties = d
        return console_output_line

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

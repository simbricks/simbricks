from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="BodyRunsFragmentsOutputArtifactSet")


@_attrs_define
class BodyRunsFragmentsOutputArtifactSet:
    """
    Attributes:
        file (list[str] | str | Unset):
    """

    file: list[str] | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file: list[str] | str | Unset
        if isinstance(self.file, Unset):
            file = UNSET
        elif isinstance(self.file, list):
            file = []
            for file_type_2_item_data in self.file:
                file_type_2_item: str
                file_type_2_item = file_type_2_item_data
                file.append(file_type_2_item)

        else:
            file = self.file

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if file is not UNSET:
            field_dict["file"] = file

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_file(data: object) -> list[str] | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                file_type_2 = []
                _file_type_2 = data
                for file_type_2_item_data in _file_type_2:

                    def _parse_file_type_2_item(data: object) -> str:
                        return cast(str, data)

                    file_type_2_item = _parse_file_type_2_item(file_type_2_item_data)

                    file_type_2.append(file_type_2_item)

                return file_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | str | Unset, data)

        file = _parse_file(d.pop("file", UNSET))

        body_runs_fragments_output_artifact_set = cls(
            file=file,
        )

        body_runs_fragments_output_artifact_set.additional_properties = d
        return body_runs_fragments_output_artifact_set

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

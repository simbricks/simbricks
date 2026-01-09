from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, File, FileTypes, Unset

T = TypeVar(
    "T", bound="BodyInstantiationsFragmentInputArtifactSetNsNsPathInstantiationsInstIdFragmentsFragIdInputArtifactPut"
)


@_attrs_define
class BodyInstantiationsFragmentInputArtifactSetNsNsPathInstantiationsInstIdFragmentsFragIdInputArtifactPut:
    """
    Attributes:
        file (File | list[File | str] | str | Unset):
    """

    file: File | list[File | str] | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file: FileTypes | list[FileTypes | str] | str | Unset
        if isinstance(self.file, Unset):
            file = UNSET
        elif isinstance(self.file, File):
            file = self.file.to_tuple()

        elif isinstance(self.file, list):
            file = []
            for file_type_2_item_data in self.file:
                file_type_2_item: FileTypes | str
                if isinstance(file_type_2_item_data, File):
                    file_type_2_item = file_type_2_item_data.to_tuple()

                else:
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

        def _parse_file(data: object) -> File | list[File | str] | str | Unset:
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, bytes):
                    raise TypeError()
                file_type_0 = File(payload=BytesIO(data))

                return file_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, list):
                    raise TypeError()
                file_type_2 = []
                _file_type_2 = data
                for file_type_2_item_data in _file_type_2:

                    def _parse_file_type_2_item(data: object) -> File | str:
                        try:
                            if not isinstance(data, bytes):
                                raise TypeError()
                            file_type_2_item_type_1 = File(payload=BytesIO(data))

                            return file_type_2_item_type_1
                        except (TypeError, ValueError, AttributeError, KeyError):
                            pass
                        return cast(File | str, data)

                    file_type_2_item = _parse_file_type_2_item(file_type_2_item_data)

                    file_type_2.append(file_type_2_item)

                return file_type_2
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(File | list[File | str] | str | Unset, data)

        file = _parse_file(d.pop("file", UNSET))

        body_instantiations_fragment_input_artifact_set_ns_ns_path_instantiations_inst_id_fragments_frag_id_input_artifact_put = cls(
            file=file,
        )

        body_instantiations_fragment_input_artifact_set_ns_ns_path_instantiations_inst_id_fragments_frag_id_input_artifact_put.additional_properties = d
        return body_instantiations_fragment_input_artifact_set_ns_ns_path_instantiations_inst_id_fragments_frag_id_input_artifact_put

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

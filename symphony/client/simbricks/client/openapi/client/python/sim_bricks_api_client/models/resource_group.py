from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResourceGroup")


@_attrs_define
class ResourceGroup:
    """ResourceGroup

    Attributes:
        id (None | str | Unset): API Object id
        namespace_id (None | str | Unset): API Object id
        available_cores (int | None | Unset):
        available_memory (int | None | Unset):
        cores_left (int | None | Unset):
        label (None | str | Unset):
        memory_left (int | None | Unset):
    """

    id: None | str | Unset = UNSET
    namespace_id: None | str | Unset = UNSET
    available_cores: int | None | Unset = UNSET
    available_memory: int | None | Unset = UNSET
    cores_left: int | None | Unset = UNSET
    label: None | str | Unset = UNSET
    memory_left: int | None | Unset = UNSET
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

        available_cores: int | None | Unset
        if isinstance(self.available_cores, Unset):
            available_cores = UNSET
        else:
            available_cores = self.available_cores

        available_memory: int | None | Unset
        if isinstance(self.available_memory, Unset):
            available_memory = UNSET
        else:
            available_memory = self.available_memory

        cores_left: int | None | Unset
        if isinstance(self.cores_left, Unset):
            cores_left = UNSET
        else:
            cores_left = self.cores_left

        label: None | str | Unset
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

        memory_left: int | None | Unset
        if isinstance(self.memory_left, Unset):
            memory_left = UNSET
        else:
            memory_left = self.memory_left

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if namespace_id is not UNSET:
            field_dict["namespace_id"] = namespace_id
        if available_cores is not UNSET:
            field_dict["available_cores"] = available_cores
        if available_memory is not UNSET:
            field_dict["available_memory"] = available_memory
        if cores_left is not UNSET:
            field_dict["cores_left"] = cores_left
        if label is not UNSET:
            field_dict["label"] = label
        if memory_left is not UNSET:
            field_dict["memory_left"] = memory_left

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

        def _parse_available_cores(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        available_cores = _parse_available_cores(d.pop("available_cores", UNSET))

        def _parse_available_memory(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        available_memory = _parse_available_memory(d.pop("available_memory", UNSET))

        def _parse_cores_left(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cores_left = _parse_cores_left(d.pop("cores_left", UNSET))

        def _parse_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_memory_left(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        memory_left = _parse_memory_left(d.pop("memory_left", UNSET))

        resource_group = cls(
            id=id,
            namespace_id=namespace_id,
            available_cores=available_cores,
            available_memory=available_memory,
            cores_left=cores_left,
            label=label,
            memory_left=memory_left,
        )

        resource_group.additional_properties = d
        return resource_group

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

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Fragment")


@_attrs_define
class Fragment:
    """Fragment

    Attributes:
        id (None | str | Unset): API Object id
        instantiation_id (None | str | Unset): API Object id
        object_id (int | None | Unset): Python objects id
        cores_required (int | None | Unset):
        fragment_executor_tag (None | str | Unset):
        memory_required (int | None | Unset):
        runner_tags (list[str] | None | Unset):
    """

    id: None | str | Unset = UNSET
    instantiation_id: None | str | Unset = UNSET
    object_id: int | None | Unset = UNSET
    cores_required: int | None | Unset = UNSET
    fragment_executor_tag: None | str | Unset = UNSET
    memory_required: int | None | Unset = UNSET
    runner_tags: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        instantiation_id: None | str | Unset
        if isinstance(self.instantiation_id, Unset):
            instantiation_id = UNSET
        else:
            instantiation_id = self.instantiation_id

        object_id: int | None | Unset
        if isinstance(self.object_id, Unset):
            object_id = UNSET
        else:
            object_id = self.object_id

        cores_required: int | None | Unset
        if isinstance(self.cores_required, Unset):
            cores_required = UNSET
        else:
            cores_required = self.cores_required

        fragment_executor_tag: None | str | Unset
        if isinstance(self.fragment_executor_tag, Unset):
            fragment_executor_tag = UNSET
        else:
            fragment_executor_tag = self.fragment_executor_tag

        memory_required: int | None | Unset
        if isinstance(self.memory_required, Unset):
            memory_required = UNSET
        else:
            memory_required = self.memory_required

        runner_tags: list[str] | None | Unset
        if isinstance(self.runner_tags, Unset):
            runner_tags = UNSET
        elif isinstance(self.runner_tags, list):
            runner_tags = self.runner_tags

        else:
            runner_tags = self.runner_tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if instantiation_id is not UNSET:
            field_dict["instantiation_id"] = instantiation_id
        if object_id is not UNSET:
            field_dict["object_id"] = object_id
        if cores_required is not UNSET:
            field_dict["cores_required"] = cores_required
        if fragment_executor_tag is not UNSET:
            field_dict["fragment_executor_tag"] = fragment_executor_tag
        if memory_required is not UNSET:
            field_dict["memory_required"] = memory_required
        if runner_tags is not UNSET:
            field_dict["runner_tags"] = runner_tags

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

        def _parse_instantiation_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        instantiation_id = _parse_instantiation_id(d.pop("instantiation_id", UNSET))

        def _parse_object_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        object_id = _parse_object_id(d.pop("object_id", UNSET))

        def _parse_cores_required(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cores_required = _parse_cores_required(d.pop("cores_required", UNSET))

        def _parse_fragment_executor_tag(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        fragment_executor_tag = _parse_fragment_executor_tag(d.pop("fragment_executor_tag", UNSET))

        def _parse_memory_required(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        memory_required = _parse_memory_required(d.pop("memory_required", UNSET))

        def _parse_runner_tags(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                runner_tags_type_0 = cast(list[str], data)

                return runner_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        runner_tags = _parse_runner_tags(d.pop("runner_tags", UNSET))

        fragment = cls(
            id=id,
            instantiation_id=instantiation_id,
            object_id=object_id,
            cores_required=cores_required,
            fragment_executor_tag=fragment_executor_tag,
            memory_required=memory_required,
            runner_tags=runner_tags,
        )

        fragment.additional_properties = d
        return fragment

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.fragment import Fragment


T = TypeVar("T", bound="Instantiation")


@_attrs_define
class Instantiation:
    """Instantiation

    Attributes:
        id (None | str | Unset): API Object id
        name (None | str | Unset):
        namespace_id (None | str | Unset): API Object id
        simulation_id (None | str | Unset): API Object id
        fragments (list[Fragment] | None | Unset):
        sb_json (None | str | Unset):
    """

    id: None | str | Unset = UNSET
    name: None | str | Unset = UNSET
    namespace_id: None | str | Unset = UNSET
    simulation_id: None | str | Unset = UNSET
    fragments: list[Fragment] | None | Unset = UNSET
    sb_json: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        namespace_id: None | str | Unset
        if isinstance(self.namespace_id, Unset):
            namespace_id = UNSET
        else:
            namespace_id = self.namespace_id

        simulation_id: None | str | Unset
        if isinstance(self.simulation_id, Unset):
            simulation_id = UNSET
        else:
            simulation_id = self.simulation_id

        fragments: list[dict[str, Any]] | None | Unset
        if isinstance(self.fragments, Unset):
            fragments = UNSET
        elif isinstance(self.fragments, list):
            fragments = []
            for fragments_type_0_item_data in self.fragments:
                fragments_type_0_item = fragments_type_0_item_data.to_dict()
                fragments.append(fragments_type_0_item)

        else:
            fragments = self.fragments

        sb_json: None | str | Unset
        if isinstance(self.sb_json, Unset):
            sb_json = UNSET
        else:
            sb_json = self.sb_json

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if namespace_id is not UNSET:
            field_dict["namespace_id"] = namespace_id
        if simulation_id is not UNSET:
            field_dict["simulation_id"] = simulation_id
        if fragments is not UNSET:
            field_dict["fragments"] = fragments
        if sb_json is not UNSET:
            field_dict["sb_json"] = sb_json

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fragment import Fragment

        d = dict(src_dict)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))

        def _parse_namespace_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        namespace_id = _parse_namespace_id(d.pop("namespace_id", UNSET))

        def _parse_simulation_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        simulation_id = _parse_simulation_id(d.pop("simulation_id", UNSET))

        def _parse_fragments(data: object) -> list[Fragment] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                fragments_type_0 = []
                _fragments_type_0 = data
                for fragments_type_0_item_data in _fragments_type_0:
                    fragments_type_0_item = Fragment.from_dict(fragments_type_0_item_data)

                    fragments_type_0.append(fragments_type_0_item)

                return fragments_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[Fragment] | None | Unset, data)

        fragments = _parse_fragments(d.pop("fragments", UNSET))

        def _parse_sb_json(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sb_json = _parse_sb_json(d.pop("sb_json", UNSET))

        instantiation = cls(
            id=id,
            name=name,
            namespace_id=namespace_id,
            simulation_id=simulation_id,
            fragments=fragments,
            sb_json=sb_json,
        )

        instantiation.additional_properties = d
        return instantiation

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

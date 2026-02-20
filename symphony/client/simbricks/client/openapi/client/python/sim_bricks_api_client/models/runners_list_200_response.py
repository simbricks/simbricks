from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.pagination_links import PaginationLinks
    from ..models.runner import Runner


T = TypeVar("T", bound="RunnersList200Response")


@_attrs_define
class RunnersList200Response:
    """RunnersList200Response

    Attributes:
        data (list[Runner] | None | Unset):
        links (None | PaginationLinks | Unset):
    """

    data: list[Runner] | None | Unset = UNSET
    links: None | PaginationLinks | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.pagination_links import PaginationLinks

        data: list[dict[str, Any]] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, list):
            data = []
            for data_type_0_item_data in self.data:
                data_type_0_item = data_type_0_item_data.to_dict()
                data.append(data_type_0_item)

        else:
            data = self.data

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
        from ..models.pagination_links import PaginationLinks
        from ..models.runner import Runner

        d = dict(src_dict)

        def _parse_data(data: object) -> list[Runner] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                data_type_0 = []
                _data_type_0 = data
                for data_type_0_item_data in _data_type_0:
                    data_type_0_item = Runner.from_dict(data_type_0_item_data)

                    data_type_0.append(data_type_0_item)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[Runner] | None | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

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

        runners_list_200_response = cls(
            data=data,
            links=links,
        )

        runners_list_200_response.additional_properties = d
        return runners_list_200_response

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

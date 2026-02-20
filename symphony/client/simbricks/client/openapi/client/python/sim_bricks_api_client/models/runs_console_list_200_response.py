from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.pagination_links import PaginationLinks
    from ..models.run_output import RunOutput


T = TypeVar("T", bound="RunsConsoleList200Response")


@_attrs_define
class RunsConsoleList200Response:
    """RunsConsoleList200Response

    Attributes:
        data (None | RunOutput | Unset):
        links (None | PaginationLinks | Unset):
    """

    data: None | RunOutput | Unset = UNSET
    links: None | PaginationLinks | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.pagination_links import PaginationLinks
        from ..models.run_output import RunOutput

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, RunOutput):
            data = self.data.to_dict()
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
        from ..models.run_output import RunOutput

        d = dict(src_dict)

        def _parse_data(data: object) -> None | RunOutput | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = RunOutput.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunOutput | Unset, data)

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

        runs_console_list_200_response = cls(
            data=data,
            links=links,
        )

        runs_console_list_200_response.additional_properties = d
        return runs_console_list_200_response

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

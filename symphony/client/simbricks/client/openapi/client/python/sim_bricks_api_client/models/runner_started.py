from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.runner_tag import RunnerTag


T = TypeVar("T", bound="RunnerStarted")


@_attrs_define
class RunnerStarted:
    """
    Attributes:
        plugin_tags (list[RunnerTag]):
        id (None | str | Unset): API Object id
        produced_at (datetime.datetime | Unset):
        discriminator (Literal['RunnerStarted'] | Unset):  Default: 'RunnerStarted'.
    """

    plugin_tags: list[RunnerTag]
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    discriminator: Literal["RunnerStarted"] | Unset = "RunnerStarted"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plugin_tags = []
        for plugin_tags_item_data in self.plugin_tags:
            plugin_tags_item = plugin_tags_item_data.to_dict()
            plugin_tags.append(plugin_tags_item)

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        produced_at: str | Unset = UNSET
        if not isinstance(self.produced_at, Unset):
            produced_at = self.produced_at.isoformat()

        discriminator = self.discriminator

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "plugin_tags": plugin_tags,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if produced_at is not UNSET:
            field_dict["produced_at"] = produced_at
        if discriminator is not UNSET:
            field_dict["discriminator"] = discriminator

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.runner_tag import RunnerTag

        d = dict(src_dict)
        plugin_tags = []
        _plugin_tags = d.pop("plugin_tags")
        for plugin_tags_item_data in _plugin_tags:
            plugin_tags_item = RunnerTag.from_dict(plugin_tags_item_data)

            plugin_tags.append(plugin_tags_item)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        _produced_at = d.pop("produced_at", UNSET)
        produced_at: datetime.datetime | Unset
        if isinstance(_produced_at, Unset):
            produced_at = UNSET
        else:
            produced_at = isoparse(_produced_at)

        discriminator = cast(Literal["RunnerStarted"] | Unset, d.pop("discriminator", UNSET))
        if discriminator != "RunnerStarted" and not isinstance(discriminator, Unset):
            raise ValueError(f"discriminator must match const 'RunnerStarted', got '{discriminator}'")

        runner_started = cls(
            plugin_tags=plugin_tags,
            id=id,
            produced_at=produced_at,
            discriminator=discriminator,
        )

        runner_started.additional_properties = d
        return runner_started

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.runner_status import RunnerStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.runner_tag import RunnerTag


T = TypeVar("T", bound="Runner")


@_attrs_define
class Runner:
    """Runner

    Attributes:
        id (None | str | Unset): API Object id
        namespace_id (None | str | Unset): API Object id
        resource_group_id (None | str | Unset): API Object id
        label (None | str | Unset):
        plugin_tags (list[RunnerTag] | None | Unset):
        status (None | RunnerStatus | Unset):
        tags (list[RunnerTag] | None | Unset):
    """

    id: None | str | Unset = UNSET
    namespace_id: None | str | Unset = UNSET
    resource_group_id: None | str | Unset = UNSET
    label: None | str | Unset = UNSET
    plugin_tags: list[RunnerTag] | None | Unset = UNSET
    status: None | RunnerStatus | Unset = UNSET
    tags: list[RunnerTag] | None | Unset = UNSET
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

        resource_group_id: None | str | Unset
        if isinstance(self.resource_group_id, Unset):
            resource_group_id = UNSET
        else:
            resource_group_id = self.resource_group_id

        label: None | str | Unset
        if isinstance(self.label, Unset):
            label = UNSET
        else:
            label = self.label

        plugin_tags: list[dict[str, Any]] | None | Unset
        if isinstance(self.plugin_tags, Unset):
            plugin_tags = UNSET
        elif isinstance(self.plugin_tags, list):
            plugin_tags = []
            for plugin_tags_type_0_item_data in self.plugin_tags:
                plugin_tags_type_0_item = plugin_tags_type_0_item_data.to_dict()
                plugin_tags.append(plugin_tags_type_0_item)

        else:
            plugin_tags = self.plugin_tags

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, RunnerStatus):
            status = self.status.value
        else:
            status = self.status

        tags: list[dict[str, Any]] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, list):
            tags = []
            for tags_type_0_item_data in self.tags:
                tags_type_0_item = tags_type_0_item_data.to_dict()
                tags.append(tags_type_0_item)

        else:
            tags = self.tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if namespace_id is not UNSET:
            field_dict["namespace_id"] = namespace_id
        if resource_group_id is not UNSET:
            field_dict["resource_group_id"] = resource_group_id
        if label is not UNSET:
            field_dict["label"] = label
        if plugin_tags is not UNSET:
            field_dict["plugin_tags"] = plugin_tags
        if status is not UNSET:
            field_dict["status"] = status
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.runner_tag import RunnerTag

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

        def _parse_resource_group_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        resource_group_id = _parse_resource_group_id(d.pop("resource_group_id", UNSET))

        def _parse_label(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        label = _parse_label(d.pop("label", UNSET))

        def _parse_plugin_tags(data: object) -> list[RunnerTag] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                plugin_tags_type_0 = []
                _plugin_tags_type_0 = data
                for plugin_tags_type_0_item_data in _plugin_tags_type_0:
                    plugin_tags_type_0_item = RunnerTag.from_dict(plugin_tags_type_0_item_data)

                    plugin_tags_type_0.append(plugin_tags_type_0_item)

                return plugin_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[RunnerTag] | None | Unset, data)

        plugin_tags = _parse_plugin_tags(d.pop("plugin_tags", UNSET))

        def _parse_status(data: object) -> None | RunnerStatus | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_0 = RunnerStatus(data)

                return status_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunnerStatus | Unset, data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_tags(data: object) -> list[RunnerTag] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                tags_type_0 = []
                _tags_type_0 = data
                for tags_type_0_item_data in _tags_type_0:
                    tags_type_0_item = RunnerTag.from_dict(tags_type_0_item_data)

                    tags_type_0.append(tags_type_0_item)

                return tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[RunnerTag] | None | Unset, data)

        tags = _parse_tags(d.pop("tags", UNSET))

        runner = cls(
            id=id,
            namespace_id=namespace_id,
            resource_group_id=resource_group_id,
            label=label,
            plugin_tags=plugin_tags,
            status=status,
            tags=tags,
        )

        runner.additional_properties = d
        return runner

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

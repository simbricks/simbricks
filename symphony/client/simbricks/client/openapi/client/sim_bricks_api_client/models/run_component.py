from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.run_component_commands import RunComponentCommands


T = TypeVar("T", bound="RunComponent")


@_attrs_define
class RunComponent:
    """RunComponent

    Attributes:
        commands (RunComponentCommands):
        name (str):
    """

    commands: RunComponentCommands
    name: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        commands = self.commands.to_dict()

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "commands": commands,
                "name": name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_component_commands import RunComponentCommands

        d = dict(src_dict)
        commands = RunComponentCommands.from_dict(d.pop("commands"))

        name = d.pop("name")

        run_component = cls(
            commands=commands,
            name=name,
        )

        run_component.additional_properties = d
        return run_component

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

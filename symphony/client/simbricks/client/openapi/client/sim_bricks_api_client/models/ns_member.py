from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.ns_role import NsRole

T = TypeVar("T", bound="NsMember")


@_attrs_define
class NsMember:
    """NsMember

    Attributes:
        username (str):
        email (str):
        first_name (str):
        last_name (str):
        role (NsRole): NsRole
    """

    username: str
    email: str
    first_name: str
    last_name: str
    role: NsRole
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        username = self.username

        email = self.email

        first_name = self.first_name

        last_name = self.last_name

        role = self.role.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "username": username,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        username = d.pop("username")

        email = d.pop("email")

        first_name = d.pop("first_name")

        last_name = d.pop("last_name")

        role = NsRole(d.pop("role"))

        ns_member = cls(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        ns_member.additional_properties = d
        return ns_member

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

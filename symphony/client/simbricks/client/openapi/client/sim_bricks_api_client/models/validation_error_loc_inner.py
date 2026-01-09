from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ValidationErrorLocInner")


@_attrs_define
class ValidationErrorLocInner:
    """ValidationErrorLocInner

    Attributes:
        anyof_schema_1_validator (None | str | Unset):
        anyof_schema_2_validator (int | None | Unset):
        actual_instance (Any | Unset):
        any_of_schemas (list[str] | Unset):
    """

    anyof_schema_1_validator: None | str | Unset = UNSET
    anyof_schema_2_validator: int | None | Unset = UNSET
    actual_instance: Any | Unset = UNSET
    any_of_schemas: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        anyof_schema_1_validator: None | str | Unset
        if isinstance(self.anyof_schema_1_validator, Unset):
            anyof_schema_1_validator = UNSET
        else:
            anyof_schema_1_validator = self.anyof_schema_1_validator

        anyof_schema_2_validator: int | None | Unset
        if isinstance(self.anyof_schema_2_validator, Unset):
            anyof_schema_2_validator = UNSET
        else:
            anyof_schema_2_validator = self.anyof_schema_2_validator

        actual_instance = self.actual_instance

        any_of_schemas: list[str] | Unset = UNSET
        if not isinstance(self.any_of_schemas, Unset):
            any_of_schemas = self.any_of_schemas

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if anyof_schema_1_validator is not UNSET:
            field_dict["anyof_schema_1_validator"] = anyof_schema_1_validator
        if anyof_schema_2_validator is not UNSET:
            field_dict["anyof_schema_2_validator"] = anyof_schema_2_validator
        if actual_instance is not UNSET:
            field_dict["actual_instance"] = actual_instance
        if any_of_schemas is not UNSET:
            field_dict["any_of_schemas"] = any_of_schemas

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_anyof_schema_1_validator(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        anyof_schema_1_validator = _parse_anyof_schema_1_validator(d.pop("anyof_schema_1_validator", UNSET))

        def _parse_anyof_schema_2_validator(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        anyof_schema_2_validator = _parse_anyof_schema_2_validator(d.pop("anyof_schema_2_validator", UNSET))

        actual_instance = d.pop("actual_instance", UNSET)

        any_of_schemas = cast(list[str], d.pop("any_of_schemas", UNSET))

        validation_error_loc_inner = cls(
            anyof_schema_1_validator=anyof_schema_1_validator,
            anyof_schema_2_validator=anyof_schema_2_validator,
            actual_instance=actual_instance,
            any_of_schemas=any_of_schemas,
        )

        validation_error_loc_inner.additional_properties = d
        return validation_error_loc_inner

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.validation_error_loc_inner import ValidationErrorLocInner


T = TypeVar("T", bound="ValidationError")


@_attrs_define
class ValidationError:
    """ValidationError

    Attributes:
        loc (list[ValidationErrorLocInner] | None | Unset):
        msg (None | str | Unset):
        type_ (None | str | Unset):
    """

    loc: list[ValidationErrorLocInner] | None | Unset = UNSET
    msg: None | str | Unset = UNSET
    type_: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        loc: list[dict[str, Any]] | None | Unset
        if isinstance(self.loc, Unset):
            loc = UNSET
        elif isinstance(self.loc, list):
            loc = []
            for loc_type_0_item_data in self.loc:
                loc_type_0_item = loc_type_0_item_data.to_dict()
                loc.append(loc_type_0_item)

        else:
            loc = self.loc

        msg: None | str | Unset
        if isinstance(self.msg, Unset):
            msg = UNSET
        else:
            msg = self.msg

        type_: None | str | Unset
        if isinstance(self.type_, Unset):
            type_ = UNSET
        else:
            type_ = self.type_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if loc is not UNSET:
            field_dict["loc"] = loc
        if msg is not UNSET:
            field_dict["msg"] = msg
        if type_ is not UNSET:
            field_dict["type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.validation_error_loc_inner import ValidationErrorLocInner

        d = dict(src_dict)

        def _parse_loc(data: object) -> list[ValidationErrorLocInner] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                loc_type_0 = []
                _loc_type_0 = data
                for loc_type_0_item_data in _loc_type_0:
                    loc_type_0_item = ValidationErrorLocInner.from_dict(loc_type_0_item_data)

                    loc_type_0.append(loc_type_0_item)

                return loc_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[ValidationErrorLocInner] | None | Unset, data)

        loc = _parse_loc(d.pop("loc", UNSET))

        def _parse_msg(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        msg = _parse_msg(d.pop("msg", UNSET))

        def _parse_type_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        type_ = _parse_type_(d.pop("type", UNSET))

        validation_error = cls(
            loc=loc,
            msg=msg,
            type_=type_,
        )

        validation_error.additional_properties = d
        return validation_error

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stream_create_params import StreamCreateParams


T = TypeVar("T", bound="StreamCreate")


@_attrs_define
class StreamCreate:
    """Request body for a client opening a stream to one fragment of a run.

    Attributes:
        run_fragment_id (str): API Object id
        target (str): Opaque to the backend; interpreted by the fragment executor.
        params (StreamCreateParams | Unset):
    """

    run_fragment_id: str
    target: str
    params: StreamCreateParams | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        run_fragment_id = self.run_fragment_id

        target = self.target

        params: dict[str, Any] | Unset = UNSET
        if not isinstance(self.params, Unset):
            params = self.params.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "run_fragment_id": run_fragment_id,
                "target": target,
            }
        )
        if params is not UNSET:
            field_dict["params"] = params

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stream_create_params import StreamCreateParams

        d = dict(src_dict)
        run_fragment_id = d.pop("run_fragment_id")

        target = d.pop("target")

        _params = d.pop("params", UNSET)
        params: StreamCreateParams | Unset
        if isinstance(_params, Unset):
            params = UNSET
        else:
            params = StreamCreateParams.from_dict(_params)

        stream_create = cls(
            run_fragment_id=run_fragment_id,
            target=target,
            params=params,
        )

        stream_create.additional_properties = d
        return stream_create

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

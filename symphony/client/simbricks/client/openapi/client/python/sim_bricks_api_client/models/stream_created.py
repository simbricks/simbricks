from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stream_created_params import StreamCreatedParams


T = TypeVar("T", bound="StreamCreated")


@_attrs_define
class StreamCreated:
    """A stream was opened to one fragment of a run. Delivered to the side that did
    not create it, with ``url`` carrying that side's websocket ticket: to the
    runner for client-created streams, to clients (as a from-runner event) for
    runner-created ones.

        Attributes:
            stream_id (str):
            target (str):
            url (str):
            run_fragment_id (str):
            run_id (str):
            params (StreamCreatedParams | Unset):
            id (None | str | Unset): API Object id
            produced_at (datetime.datetime | Unset):
            discriminator (Literal['StreamCreated'] | Unset):  Default: 'StreamCreated'.
    """

    stream_id: str
    target: str
    url: str
    run_fragment_id: str
    run_id: str
    params: StreamCreatedParams | Unset = UNSET
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    discriminator: Literal["StreamCreated"] | Unset = "StreamCreated"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        stream_id = self.stream_id

        target = self.target

        url = self.url

        run_fragment_id = self.run_fragment_id

        run_id = self.run_id

        params: dict[str, Any] | Unset = UNSET
        if not isinstance(self.params, Unset):
            params = self.params.to_dict()

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
                "stream_id": stream_id,
                "target": target,
                "url": url,
                "run_fragment_id": run_fragment_id,
                "run_id": run_id,
            }
        )
        if params is not UNSET:
            field_dict["params"] = params
        if id is not UNSET:
            field_dict["id"] = id
        if produced_at is not UNSET:
            field_dict["produced_at"] = produced_at
        if discriminator is not UNSET:
            field_dict["discriminator"] = discriminator

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stream_created_params import StreamCreatedParams

        d = dict(src_dict)
        stream_id = d.pop("stream_id")

        target = d.pop("target")

        url = d.pop("url")

        run_fragment_id = d.pop("run_fragment_id")

        run_id = d.pop("run_id")

        _params = d.pop("params", UNSET)
        params: StreamCreatedParams | Unset
        if isinstance(_params, Unset):
            params = UNSET
        else:
            params = StreamCreatedParams.from_dict(_params)

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
            produced_at = datetime.datetime.fromisoformat(_produced_at)

        discriminator = cast(Literal["StreamCreated"] | Unset, d.pop("discriminator", UNSET))
        if discriminator != "StreamCreated" and not isinstance(discriminator, Unset):
            raise ValueError(f"discriminator must match const 'StreamCreated', got '{discriminator}'")

        stream_created = cls(
            stream_id=stream_id,
            target=target,
            url=url,
            run_fragment_id=run_fragment_id,
            run_id=run_id,
            params=params,
            id=id,
            produced_at=produced_at,
            discriminator=discriminator,
        )

        stream_created.additional_properties = d
        return stream_created

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

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stream_params import StreamParams


T = TypeVar("T", bound="Stream")


@_attrs_define
class Stream:
    """A bidirectional, non-persisted byte stream between a client and the fragment
    executor running one fragment of a run. ``url`` carries the websocket ticket of
    the side that created the stream; the other side receives its own ticket in a
    StreamCreated event.

        Attributes:
            id (None | str | Unset): API Object id
            run_id (None | str | Unset): API Object id
            run_fragment_id (None | str | Unset): API Object id
            target (None | str | Unset): Opaque to the backend; interpreted by the two ends only.
            params (StreamParams | Unset):
            url (None | str | Unset): Websocket URL carrying the caller's ticket.
    """

    id: None | str | Unset = UNSET
    run_id: None | str | Unset = UNSET
    run_fragment_id: None | str | Unset = UNSET
    target: None | str | Unset = UNSET
    params: StreamParams | Unset = UNSET
    url: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        run_id: None | str | Unset
        if isinstance(self.run_id, Unset):
            run_id = UNSET
        else:
            run_id = self.run_id

        run_fragment_id: None | str | Unset
        if isinstance(self.run_fragment_id, Unset):
            run_fragment_id = UNSET
        else:
            run_fragment_id = self.run_fragment_id

        target: None | str | Unset
        if isinstance(self.target, Unset):
            target = UNSET
        else:
            target = self.target

        params: dict[str, Any] | Unset = UNSET
        if not isinstance(self.params, Unset):
            params = self.params.to_dict()

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if run_id is not UNSET:
            field_dict["run_id"] = run_id
        if run_fragment_id is not UNSET:
            field_dict["run_fragment_id"] = run_fragment_id
        if target is not UNSET:
            field_dict["target"] = target
        if params is not UNSET:
            field_dict["params"] = params
        if url is not UNSET:
            field_dict["url"] = url

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stream_params import StreamParams

        d = dict(src_dict)

        def _parse_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        id = _parse_id(d.pop("id", UNSET))

        def _parse_run_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        run_id = _parse_run_id(d.pop("run_id", UNSET))

        def _parse_run_fragment_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        run_fragment_id = _parse_run_fragment_id(d.pop("run_fragment_id", UNSET))

        def _parse_target(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        target = _parse_target(d.pop("target", UNSET))

        _params = d.pop("params", UNSET)
        params: StreamParams | Unset
        if isinstance(_params, Unset):
            params = UNSET
        else:
            params = StreamParams.from_dict(_params)

        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))

        stream = cls(
            id=id,
            run_id=run_id,
            run_fragment_id=run_fragment_id,
            target=target,
            params=params,
            url=url,
        )

        stream.additional_properties = d
        return stream

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

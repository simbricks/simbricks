from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.run_component_state import RunComponentState
from ..types import UNSET, Unset

T = TypeVar("T", bound="ProxyStateChange")


@_attrs_define
class ProxyStateChange:
    """
    Attributes:
        ip (str):
        port (int):
        state (RunComponentState):
        proxy_id (int):
        run_id (str):
        proxy_name (str):
        id (None | str | Unset): API Object id
        produced_at (datetime.datetime | Unset):
        discriminator (Literal['ProxyStateChange'] | Unset):  Default: 'ProxyStateChange'.
        command (None | str | Unset):
    """

    ip: str
    port: int
    state: RunComponentState
    proxy_id: int
    run_id: str
    proxy_name: str
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    discriminator: Literal["ProxyStateChange"] | Unset = "ProxyStateChange"
    command: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        ip = self.ip

        port = self.port

        state = self.state.value

        proxy_id = self.proxy_id

        run_id = self.run_id

        proxy_name = self.proxy_name

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        produced_at: str | Unset = UNSET
        if not isinstance(self.produced_at, Unset):
            produced_at = self.produced_at.isoformat()

        discriminator = self.discriminator

        command: None | str | Unset
        if isinstance(self.command, Unset):
            command = UNSET
        else:
            command = self.command

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ip": ip,
                "port": port,
                "state": state,
                "proxy_id": proxy_id,
                "run_id": run_id,
                "proxy_name": proxy_name,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if produced_at is not UNSET:
            field_dict["produced_at"] = produced_at
        if discriminator is not UNSET:
            field_dict["discriminator"] = discriminator
        if command is not UNSET:
            field_dict["command"] = command

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        ip = d.pop("ip")

        port = d.pop("port")

        state = RunComponentState(d.pop("state"))

        proxy_id = d.pop("proxy_id")

        run_id = d.pop("run_id")

        proxy_name = d.pop("proxy_name")

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

        discriminator = cast(Literal["ProxyStateChange"] | Unset, d.pop("discriminator", UNSET))
        if discriminator != "ProxyStateChange" and not isinstance(discriminator, Unset):
            raise ValueError(f"discriminator must match const 'ProxyStateChange', got '{discriminator}'")

        def _parse_command(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        command = _parse_command(d.pop("command", UNSET))

        proxy_state_change = cls(
            ip=ip,
            port=port,
            state=state,
            proxy_id=proxy_id,
            run_id=run_id,
            proxy_name=proxy_name,
            id=id,
            produced_at=produced_at,
            discriminator=discriminator,
            command=command,
        )

        proxy_state_change.additional_properties = d
        return proxy_state_change

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

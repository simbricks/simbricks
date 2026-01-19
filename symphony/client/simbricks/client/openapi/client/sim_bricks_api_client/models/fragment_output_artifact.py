from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, Literal, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="FragmentOutputArtifact")


@_attrs_define
class FragmentOutputArtifact:
    """
    Attributes:
        artifact (str):
        artifact_name (str):
        run_fragment_id (str):
        run_id (str):
        id (None | str | Unset): API Object id
        produced_at (datetime.datetime | Unset):
        discriminator (Literal['FragmentOutputArtifact'] | Unset):  Default: 'FragmentOutputArtifact'.
    """

    artifact: str
    artifact_name: str
    run_fragment_id: str
    run_id: str
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    discriminator: Literal["FragmentOutputArtifact"] | Unset = "FragmentOutputArtifact"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        artifact = self.artifact

        artifact_name = self.artifact_name

        run_fragment_id = self.run_fragment_id

        run_id = self.run_id

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
                "artifact": artifact,
                "artifact_name": artifact_name,
                "run_fragment_id": run_fragment_id,
                "run_id": run_id,
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
        d = dict(src_dict)
        artifact = d.pop("artifact")

        artifact_name = d.pop("artifact_name")

        run_fragment_id = d.pop("run_fragment_id")

        run_id = d.pop("run_id")

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

        discriminator = cast(Literal["FragmentOutputArtifact"] | Unset, d.pop("discriminator", UNSET))
        if discriminator != "FragmentOutputArtifact" and not isinstance(discriminator, Unset):
            raise ValueError(f"discriminator must match const 'FragmentOutputArtifact', got '{discriminator}'")

        fragment_output_artifact = cls(
            artifact=artifact,
            artifact_name=artifact_name,
            run_fragment_id=run_fragment_id,
            run_id=run_id,
            id=id,
            produced_at=produced_at,
            discriminator=discriminator,
        )

        fragment_output_artifact.additional_properties = d
        return fragment_output_artifact

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

from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.instantiation import Instantiation
    from ..models.run_fragment import RunFragment
    from ..models.simulation import Simulation
    from ..models.system import System


T = TypeVar("T", bound="StartRunReq")


@_attrs_define
class StartRunReq:
    """
    Attributes:
        run_id (int):
        system (System): System
        simulation (Simulation): Simulation
        fragments (list[RunFragment]):
        inst (Instantiation): Instantiation
        id (None | str | Unset): API Object id
        produced_at (datetime.datetime | Unset):
    """

    run_id: int
    system: System
    simulation: Simulation
    fragments: list[RunFragment]
    inst: Instantiation
    id: None | str | Unset = UNSET
    produced_at: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        run_id = self.run_id

        system = self.system.to_dict()

        simulation = self.simulation.to_dict()

        fragments = []
        for fragments_item_data in self.fragments:
            fragments_item = fragments_item_data.to_dict()
            fragments.append(fragments_item)

        inst = self.inst.to_dict()

        id: None | str | Unset
        if isinstance(self.id, Unset):
            id = UNSET
        else:
            id = self.id

        produced_at: str | Unset = UNSET
        if not isinstance(self.produced_at, Unset):
            produced_at = self.produced_at.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "run_id": run_id,
                "system": system,
                "simulation": simulation,
                "fragments": fragments,
                "inst": inst,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if produced_at is not UNSET:
            field_dict["produced_at"] = produced_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.instantiation import Instantiation
        from ..models.run_fragment import RunFragment
        from ..models.simulation import Simulation
        from ..models.system import System

        d = dict(src_dict)
        run_id = d.pop("run_id")

        system = System.from_dict(d.pop("system"))

        simulation = Simulation.from_dict(d.pop("simulation"))

        fragments = []
        _fragments = d.pop("fragments")
        for fragments_item_data in _fragments:
            fragments_item = RunFragment.from_dict(fragments_item_data)

            fragments.append(fragments_item)

        inst = Instantiation.from_dict(d.pop("inst"))

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

        start_run_req = cls(
            run_id=run_id,
            system=system,
            simulation=simulation,
            fragments=fragments,
            inst=inst,
            id=id,
            produced_at=produced_at,
        )

        start_run_req.additional_properties = d
        return start_run_req

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

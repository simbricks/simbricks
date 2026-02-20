from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.run_output_proxies_type_0 import RunOutputProxiesType0
    from ..models.run_output_simulators_type_0 import RunOutputSimulatorsType0


T = TypeVar("T", bound="RunOutput")


@_attrs_define
class RunOutput:
    """RunOutput

    Attributes:
        run_id (int):
        proxies (None | RunOutputProxiesType0 | Unset):
        simulators (None | RunOutputSimulatorsType0 | Unset):
    """

    run_id: int
    proxies: None | RunOutputProxiesType0 | Unset = UNSET
    simulators: None | RunOutputSimulatorsType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.run_output_proxies_type_0 import RunOutputProxiesType0
        from ..models.run_output_simulators_type_0 import RunOutputSimulatorsType0

        run_id = self.run_id

        proxies: dict[str, Any] | None | Unset
        if isinstance(self.proxies, Unset):
            proxies = UNSET
        elif isinstance(self.proxies, RunOutputProxiesType0):
            proxies = self.proxies.to_dict()
        else:
            proxies = self.proxies

        simulators: dict[str, Any] | None | Unset
        if isinstance(self.simulators, Unset):
            simulators = UNSET
        elif isinstance(self.simulators, RunOutputSimulatorsType0):
            simulators = self.simulators.to_dict()
        else:
            simulators = self.simulators

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "run_id": run_id,
            }
        )
        if proxies is not UNSET:
            field_dict["proxies"] = proxies
        if simulators is not UNSET:
            field_dict["simulators"] = simulators

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.run_output_proxies_type_0 import RunOutputProxiesType0
        from ..models.run_output_simulators_type_0 import RunOutputSimulatorsType0

        d = dict(src_dict)
        run_id = d.pop("run_id")

        def _parse_proxies(data: object) -> None | RunOutputProxiesType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                proxies_type_0 = RunOutputProxiesType0.from_dict(data)

                return proxies_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunOutputProxiesType0 | Unset, data)

        proxies = _parse_proxies(d.pop("proxies", UNSET))

        def _parse_simulators(data: object) -> None | RunOutputSimulatorsType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                simulators_type_0 = RunOutputSimulatorsType0.from_dict(data)

                return simulators_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | RunOutputSimulatorsType0 | Unset, data)

        simulators = _parse_simulators(d.pop("simulators", UNSET))

        run_output = cls(
            run_id=run_id,
            proxies=proxies,
            simulators=simulators,
        )

        run_output.additional_properties = d
        return run_output

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

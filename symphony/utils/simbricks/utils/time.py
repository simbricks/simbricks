# Copyright 2026 Max Planck Institute for Software Systems,
# National University of Singapore, and SimBricks UG (haftungsbeschränkt)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import decimal
import functools
import re
import typing as tp

import typing_extensions as tpe

from simbricks.utils import base as utils_base


@functools.total_ordering
class TimeInterval:
    """An immutable time interval, stored as an integer number of picoseconds.

    Instances are created through the per-unit factory methods (``TimeInterval.ns(500)``)
    or by parsing a unit suffixed string (``TimeInterval.parse("500ns")``). Bare numbers
    are deliberately not accepted anywhere, they leave the unit implicit.
    """

    _UNITS: tp.ClassVar[dict[str, int]] = {
        "ps": 1,
        "ns": 10**3,
        "us": 10**6,
        "ms": 10**9,
        "s": 10**12,
    }
    _PATTERN: tp.ClassVar[re.Pattern] = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ps|ns|us|ms|s)\s*$")

    __slots__ = ("_picoseconds",)

    def __init__(self, picoseconds: int) -> None:
        if isinstance(picoseconds, bool) or not isinstance(picoseconds, int):
            raise TypeError(f"picoseconds must be an int, got {type(picoseconds)}")
        if picoseconds < 0:
            raise ValueError(f"time interval must not be negative, got {picoseconds}ps")
        object.__setattr__(self, "_picoseconds", picoseconds)

    def __setattr__(self, name: str, value: tp.Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    @property
    def picoseconds(self) -> int:
        """The interval as a whole number of picoseconds."""
        return self._picoseconds

    @classmethod
    def _from_decimal(cls, amount: decimal.Decimal, unit: str, label: str) -> tpe.Self:
        picoseconds = amount * cls._UNITS[unit]
        if picoseconds != picoseconds.to_integral_value():
            raise ValueError(f"{label} is not a whole number of picoseconds")
        return cls(int(picoseconds))

    @classmethod
    def _from_amount(cls, amount: int | float, unit: str) -> tpe.Self:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError(f"time amount must be an int or float, got {type(amount)}")
        return cls._from_decimal(decimal.Decimal(str(amount)), unit, f"{amount}{unit}")

    @classmethod
    def ps(cls, amount: int | float) -> tpe.Self:
        return cls._from_amount(amount, "ps")

    @classmethod
    def ns(cls, amount: int | float) -> tpe.Self:
        return cls._from_amount(amount, "ns")

    @classmethod
    def us(cls, amount: int | float) -> tpe.Self:
        return cls._from_amount(amount, "us")

    @classmethod
    def ms(cls, amount: int | float) -> tpe.Self:
        return cls._from_amount(amount, "ms")

    @classmethod
    def s(cls, amount: int | float) -> tpe.Self:
        return cls._from_amount(amount, "s")

    @classmethod
    def parse(cls, value: str) -> tpe.Self:
        """Parse a unit suffixed string like ``"500ns"`` or ``"1.5us"``."""
        if not isinstance(value, str):
            raise TypeError(f"time interval string must be a str, got {type(value)}")
        match = cls._PATTERN.match(value)
        if match is None:
            raise ValueError(
                f"cannot parse '{value}' as a time interval, expected an amount followed by one of"
                f" {', '.join(cls._UNITS)}, e.g. '500ns'"
            )
        return cls._from_decimal(decimal.Decimal(match.group(1)), match.group(2), value.strip())

    @classmethod
    def from_value(cls, value: "TimeInterval | str") -> "TimeInterval":
        """Coerce the accepted user facing representations into a ``Time``."""
        if isinstance(value, TimeInterval):
            return value
        if isinstance(value, str):
            return cls.parse(value)
        raise TypeError(
            f"time interval must be a {cls.__name__} instance or a unit suffixed string like"
            f" '500ns', got {type(value)}"
        )

    def __str__(self) -> str:
        for unit, factor in reversed(self._UNITS.items()):
            if self._picoseconds % factor == 0:
                return f"{self._picoseconds // factor}{unit}"
        return f"{self._picoseconds}ps"

    def __repr__(self) -> str:
        return f"{type(self).__name__}.parse('{self}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimeInterval):
            return NotImplemented
        return self._picoseconds == other._picoseconds

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TimeInterval):
            return NotImplemented
        return self._picoseconds < other._picoseconds

    def __hash__(self) -> int:
        return hash(self._picoseconds)

    def __bool__(self) -> bool:
        return self._picoseconds != 0

    def __add__(self, other: "TimeInterval") -> "TimeInterval":
        if not isinstance(other, TimeInterval):
            return NotImplemented
        return TimeInterval(self._picoseconds + other._picoseconds)

    def __sub__(self, other: "TimeInterval") -> "TimeInterval":
        if not isinstance(other, TimeInterval):
            return NotImplemented
        return TimeInterval(self._picoseconds - other._picoseconds)

    def __mul__(self, factor: int | float) -> "TimeInterval":
        if isinstance(factor, bool) or not isinstance(factor, (int, float)):
            return NotImplemented
        picoseconds = decimal.Decimal(self._picoseconds) * decimal.Decimal(str(factor))
        if picoseconds != picoseconds.to_integral_value():
            raise ValueError(f"scaling {self} by {factor} is not a whole number of picoseconds")
        return TimeInterval(int(picoseconds))

    __rmul__ = __mul__

    def toJSON(self) -> dict:
        return {
            "type": type(self).__qualname__,
            "module": type(self).__module__,
            "picoseconds": self._picoseconds,
        }

    @classmethod
    def fromJSON(cls, json_obj: dict) -> tpe.Self:
        if not isinstance(json_obj, dict):
            raise TypeError(
                f"cannot deserialize a time interval from {type(json_obj)}. Time intervals are"
                " serialized as objects carrying a 'picoseconds' field. A bare number most likely"
                " stems from an outdated configuration that stored nanoseconds."
            )
        return cls(int(utils_base.get_json_attr_top(json_obj, "picoseconds")))

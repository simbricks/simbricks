# Copyright 2024 Max Planck Institute for Software Systems, and
# National University of Singapore
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

import abc
import importlib.util
import itertools
import importlib
import typing as tp
import typing_extensions as tpe
import enum


class IdObj(abc.ABC):
    __id_iter = itertools.count()

    def __init__(self):
        self._id = next(self.__id_iter)
        self._is_dummy: bool = False

    def id(self) -> int:
        return self._id

    def toJSON(self):
        json_obj = {}
        json_obj["type"] = self.__class__.__qualname__
        json_obj["module"] = self.__class__.__module__
        json_obj["id"] = self._id
        json_obj["is_dummy"] = self._is_dummy
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj) -> tpe.Self:
        instance = cls.__new__(cls)
        instance._id = get_json_attr_top(json_obj, "id")
        instance._is_dummy = bool(get_json_attr_top(json_obj, "is_dummy"))
        return instance


class Time(enum.IntEnum):
    Picoseconds = 10 ** (-3)
    Nanoseconds = 1
    Microseconds = 10 ** (3)
    Milliseconds = 10 ** (6)
    Seconds = 10 ** (9)


def filter_None_dict(to_filter: dict) -> dict:
    res = {k: v for k, v in to_filter.items() if v is not None}
    return res


def check_type(obj, expected_type) -> bool:
    """
    Checks if obj has type or is a subtype of expected_type
    obj: an class object
    expected_type: a type object
    """
    return isinstance(obj, expected_type)


def check_types(obj, *expected_types) -> bool:
    """
    Checks if obj has type or is a subtype of any of expected_types
    obj: an class object
    expected_types: list of type objects
    """
    for exp_ty in expected_types:
        if check_type(obj, expected_type=exp_ty):
            return True

    return False


def has_expected_type(obj, expected_type) -> None:
    if not check_type(obj=obj, expected_type=expected_type):
        raise Exception(
            f"obj of type {type(obj)} has not the type or is not a subtype of {expected_type}"
        )


def has_attribute(obj, attr: str) -> None:
    if not hasattr(obj, attr):
        raise Exception(f"obj of type {type(obj)} no attribute called {attr}")


def get_json_attr_top_or_none(json_obj: dict, attr: str) -> tp.Any | None:
    if attr in json_obj:
        return json_obj[attr]

    return None


def has_json_attr_top(json_obj: dict, attr: str) -> None:
    if not attr in json_obj:
        raise Exception(f"{json_obj} does not contain key {attr}")


def get_json_attr_top(json_obj: dict, attr: str) -> tp.Any:
    has_json_attr_top(json_obj, attr)
    return json_obj[attr]


def get_cls_from_type_module(type_name: str, module_name: str, required: bool) -> tp.Any:

    spec = None
    try:
        spec = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ValueError):
        pass

    if spec is None:
        if required:
            raise Exception(f'could not load module "{module_name}"')
        return None
    # Import the module
    module = importlib.import_module(module_name)

    if not hasattr(module, type_name):
        if required:
            raise Exception(f'module "{module_name}" has no attribute "{type_name}"')
        return None
    # Get the class from the module
    cls = getattr(module, type_name)

    return cls


def get_cls_by_json(json_obj: dict, required: bool = True) -> tp.Any:
    type_name = get_json_attr_top(json_obj, "type")
    module_name = get_json_attr_top(json_obj, "module")
    return get_cls_from_type_module(type_name, module_name, required)


def _has_base_type(obj: tp.Any) -> bool:
    return isinstance(obj, (str, int, float, bool, type(None)))


def _obj_to_json(obj: tp.Any) -> tp.Any:
    if _has_base_type(obj):
        return obj
    elif isinstance(obj, list):
        return list_tuple_to_json(obj)
    elif isinstance(obj, tuple):
        return list_tuple_to_json(obj)
    elif isinstance(obj, dict):
        return dict_to_json(obj)
    else:
        has_attribute(obj, "toJSON")
        return obj.toJSON()


def list_tuple_to_json(list: list | tuple) -> list:
    json_list = []
    for element in list:
        json_list.append(_obj_to_json(element))

    return json_list


def dict_to_json(data: dict) -> dict:
    json_obj = {}
    for key, value in data.items():
        key_json = _obj_to_json(key)
        value_json = _obj_to_json(value)
        assert key_json not in json_obj
        json_obj[key_json] = value_json

    return json_obj


def _json_obj_to_dict(obj: tp.Any) -> tp.Any:
    if _has_base_type(obj):
        return obj
    elif isinstance(obj, list):
        return json_array_to_list(obj)
    elif isinstance(obj, dict):
        return _json_dict_to_obj(obj)
    else:
        raise ValueError(f"cannot parse object with type {type(obj)} from json")


def _json_dict_to_obj(json_obj: dict) -> tp.Any:
    if "type" in json_obj and "module" in json_obj:
        # this seems to be a Python object that was converted to JSON
        cls = get_cls_from_type_module(json_obj["type"], json_obj["module"])
        has_attribute(cls, "fromJSON")
        return cls.fromJSON(json_obj)
    else:
        # this seems to be a plain dict
        return json_to_dict(json_obj)


def json_array_to_list(array: list) -> list:
    data = []
    for element in array:
        data.append(_json_obj_to_dict(element))

    return data


def json_to_dict(json_obj: dict) -> dict:
    data = {}
    for key, value in json_obj.items():
        key_dict = _json_obj_to_dict(key)
        value_dict = _json_obj_to_dict(value)
        assert key_dict not in data
        data[key_dict] = value_dict

    return data


ET = tp.TypeVar("ET", bound=enum.Enum)


def enum_subs(enum_class: tp.Type[ET], *exclude_values: tuple[ET]) -> list[ET]:
    res = list(filter(lambda ty: ty not in exclude_values, enum_class))
    return res

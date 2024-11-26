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
import itertools
import importlib


class IdObj(abc.ABC):
    __id_iter = itertools.count()

    def __init__(self):
        self._id = next(self.__id_iter)

    def id(self) -> int:
        return self._id

    def toJSON(self):
        json_obj = {}
        json_obj["id"] = self._id
        return json_obj

    @classmethod
    def fromJSON(cls, json_obj):
        instance = cls.__new__(cls)
        instance._id = get_json_attr_top(json_obj, "id")
        return instance


def check_type(obj, expected_type) -> bool:
    """
    Checks if obj has type or is a subtype of expected_type
    obj: an class object
    expected_type: a type object
    """
    return isinstance(obj, expected_type)


def has_expected_type(obj, expected_type) -> None:
    if not check_type(obj=obj, expected_type=expected_type):
        raise Exception(
            f"obj of type {type(obj)} has not the type or is not a subtype of {expected_type}"
        )


def has_attribute(obj, attr: str) -> None:
    if not hasattr(obj, attr):
        raise Exception(f"obj of type {type(obj)} no attribute called {attr}")


def get_json_attr_top_or_none(json_obj: dict, attr: str) -> dict | None:
    if attr in json_obj:
        return json_obj[attr]

    return None


def has_json_attr_top(json_obj: dict, attr: str) -> None:
    if not attr in json_obj:
        raise Exception(f"{json_obj} does not contain key {attr}")


def get_json_attr_top(json_obj: dict, attr: str) -> dict:
    has_json_attr_top(json_obj, attr)
    return json_obj[attr]


def get_cls_from_type_module(type_name: str, module_name: str):
    # Import the module
    module = importlib.import_module(module_name)

    # Get the class from the module
    cls = getattr(module, type_name)

    return cls


def get_cls_by_json(json_obj: dict):
    type_name = get_json_attr_top(json_obj, "type")
    module_name = get_json_attr_top(json_obj, "module")
    return get_cls_from_type_module(type_name, module_name)

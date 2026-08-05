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

import contextlib
import typing
from typing import TypeVar

import httpx

from simbricks.client.openapi.client.python.sim_bricks_api_client.client import AuthenticatedClient
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    HTTPValidationError,
    InlineObject,
)

from .auth import simbricks_httpx_auth
from .settings import client_settings


@contextlib.contextmanager
def non_close_file(handle: typing.IO):
    close_fn = handle.close
    handle.close = lambda: handle.seek(0)
    try:
        yield handle
    finally:
        handle.close = close_fn


T = TypeVar("T")


def _raise_unexpected(response_model: object):
    raise RuntimeError(f"encountered unexpected repsonse model: {response_model}")


def check_response_error(response_model: object) -> None:
    """Raise for the server's known error response models.

    Shared by :func:`validate_response_model` and :func:`validate_no_response_model`.
    """
    match response_model:
        case HTTPValidationError():
            raise RuntimeError(f"encountered http validation error: {response_model.detail}")
        case InlineObject():
            raise RuntimeError(f"encountered error: {response_model.detail}")


def validate_response_model(response_model: object, expected_type: type[T]) -> T | None:
    """Validate a response expected to carry a model of ``expected_type``.

    Returns the model on success and raises if the server returned an error model
    or anything unexpected.
    """
    if isinstance(response_model, expected_type):
        return response_model

    check_response_error(response_model)
    _raise_unexpected(response_model)


def validate_no_response_model(response_model: object | None) -> None:
    """Validate a response expected to carry no content (``None``).

    Use for endpoints whose success case returns ``None`` (e.g. uploads/setters).
    Raises if the server returned an error model, or any other unexpected content.
    """
    if response_model is None:
        return

    check_response_error(response_model)
    _raise_unexpected(response_model)


@contextlib.asynccontextmanager
async def base_client(
    base_url: str = client_settings().base_url, timeout_sec: int = client_settings().timeout_sec
) -> typing.AsyncIterator[AuthenticatedClient]:

    # custom httpx client using our authentication class
    sb_auth = simbricks_httpx_auth()
    httpx_client = httpx.AsyncClient(base_url=base_url, auth=sb_auth, timeout=timeout_sec)

    # create the auto generated client instance to pass on
    client = AuthenticatedClient(
        base_url=base_url, raise_on_unexpected_status=True, token="invalid"
    )
    client.set_async_httpx_client(httpx_client)

    async with client as client:
        yield client

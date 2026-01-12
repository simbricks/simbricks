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

import httpx
import typing
import contextlib
from typing import TypeVar
from .settings import client_settings
from .auth import TokenProvider, SimBricksAuth
from simbricks.client.openapi.client.sim_bricks_api_client.client import AuthenticatedClient
from simbricks.client.openapi.client.sim_bricks_api_client.models import (
    HTTPValidationError,
    InlineObject,
)


@contextlib.contextmanager
def non_close_file(handle: typing.IO):
    close_fn = handle.close
    handle.close = lambda: handle.seek(0)
    try:
        yield handle
    finally:
        handle.close = close_fn


T = TypeVar("T")


def validate_response_model(response_model: object, expected_type: type[T]) -> T:
    match response_model:
        case expected_type():
            return response_model
        case HTTPValidationError():
            raise Exception(f"encountered http validation error: {response_model}")
        case InlineObject():
            raise Exception(f"encountered unexpected InlineObject: {response_model}")
        case _:
            raise Exception(f"encountered unexpected repsonse model: {response_model}")


__token_provider = TokenProvider()
__simbricks_auth = SimBricksAuth(__token_provider)


@contextlib.asynccontextmanager
async def base_client(
    base_url: str = client_settings().base_url,
) -> typing.AsyncIterator[AuthenticatedClient]:

    access_token = await __token_provider.access_token()

    # custom httpx client using our authentication class
    httpx_client = httpx.AsyncClient(base_url=base_url, auth=__simbricks_auth)

    # create the auto generated client instance to pass on
    client = AuthenticatedClient(
        base_url=base_url, raise_on_unexpected_status=True, token=access_token
    )
    client.set_async_httpx_client(httpx_client)

    async with client as client:
        yield client

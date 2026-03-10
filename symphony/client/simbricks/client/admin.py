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


from .base import base_client, validate_response_model
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.admin import (
    admin_namespaces_create,
    admin_namespaces_get_name,
    admin_namespaces_get_id,
    admin_namespaces_list,
    admin_namespaces_schedule,
    admin_namespaces_delete,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    Namespace,
    NamespacesList200Response,
)


class AdminClient:

    def __init__(self):
        pass

    async def get_ns(self, ns_id: str) -> Namespace | None:
        async with base_client() as client:
            ns = await admin_namespaces_get_id.asyncio(ns_id, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    async def get_ns_by_name(self, ns_path: str) -> Namespace | None:
        async with base_client() as client:
            ns = await admin_namespaces_get_name.asyncio(ns_path, client=client)
            ns = validate_response_model(ns, Namespace)
            return ns

    async def get_all_ns(self) -> NamespacesList200Response:
        async with base_client() as client:
            response = await admin_namespaces_list.asyncio(client=client)
            response = validate_response_model(response, NamespacesList200Response)
            return response

    async def create_ns(self, parent_id: str | None, name: str) -> Namespace:
        to_create = Namespace(name=name, parent_id=parent_id)
        async with base_client() as client:
            ns = await admin_namespaces_create.asyncio(client=client, body=to_create)
            ns = validate_response_model(ns, Namespace)
            if ns is None:
                raise Exception(f"Namespace {name} could not be created")
            return ns

    async def delete(self, ns_id: str) -> None:
        async with base_client() as client:
            await admin_namespaces_delete.asyncio(ns_id, client=client)

    async def schedule_ns(self, ns_id: str) -> None:
        async with base_client() as client:
            await admin_namespaces_schedule.asyncio(ns_id, client=client)


async def admin_client() -> AdminClient:
    return AdminClient()

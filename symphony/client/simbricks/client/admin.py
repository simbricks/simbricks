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
from simbricks.client.openapi.client.sim_bricks_api_client.api.admin import (
    create_ns_admin_post_admin_post as create_ns,
    get_ns_admin_get_admin_get as get_ns_list,
    get_ns_admin_ns_id_get_admin_ns_id_get as get_ns_id,
    get_ns_by_name_admin_name_ns_name_get_admin_name_ns_path_get as get_by_name,
    schedule_ns_admin_ns_id_schedule_post_admin_ns_id_schedule_post as ns_schedule,
    delete_ns_admin_ns_id_delete_admin_ns_id_delete as delete_ns,
)
from simbricks.client.openapi.client.sim_bricks_api_client.models import (
    Namespace,
    NamespacesList200Response,
)


class AdminClient:

    def __init__(self):
        pass

    async def get_ns(self, ns_id: str) -> Namespace:
        async with base_client() as client:
            ns = await get_ns_id.asyncio(ns_id, client=client)
            return ns

    async def get_ns_by_name(self, ns_path: str) -> Namespace:
        async with base_client() as client:
            ns = await get_by_name.asyncio(ns_path, client=client)
            return ns

    async def get_all_ns(self) -> NamespacesList200Response:
        async with base_client() as client:
            response = await get_ns_list.asyncio(client=client)
            response = validate_response_model(response, NamespacesList200Response)
            return response

    async def create_ns(self, parent_id: str | None, name: str) -> Namespace:
        to_create = Namespace(name=name, parent_id=parent_id)
        async with base_client() as client:
            ns = await create_ns.asyncio(client=client, body=to_create)
            return ns

    async def delete(self, ns_id: str) -> None:
        async with base_client() as client:
            await delete_ns.asyncio(ns_id, client=client)

    async def schedule_ns(self, ns_id: str) -> None:
        async with base_client() as client:
            await ns_schedule.asyncio(ns_id, client=client)


def admin_client() -> AdminClient:
    return AdminClient()

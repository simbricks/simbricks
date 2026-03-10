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
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.user import (
    user_default_membership,
    user_info,
    user_ns_memberships,
    set_user_default_membership,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    MembersList200Response,
    NsMember,
    User,
)


class UserClient:

    def __init__(self):
        pass

    async def user_info(self) -> User:
        async with base_client() as client:
            user = await user_info.asyncio(client=client)
            user = validate_response_model(user, User)
            return user

    async def default_namespace_membership(self) -> NsMember:
        async with base_client() as client:
            default_membership = await user_default_membership.asyncio(client=client)
            default_membership = validate_response_model(default_membership, NsMember)
            return default_membership
        
    async def memberships(self) -> MembersList200Response:
        async with base_client() as client:
            memberships = await user_ns_memberships.asyncio(client=client)
            memberships = validate_response_model(memberships, MembersList200Response)
            return memberships
        
    async def set_default_ns_membership(self, ns_path: str) -> NsMember:
        async with base_client() as client:
            default_membership = await set_user_default_membership.asyncio(ns_path, client=client)
            default_membership = validate_response_model(default_membership, NsMember)
            return default_membership


async def user_client() -> UserClient:
    return UserClient()

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
from .auth import Token
from simbricks.client.openapi.client.python.sim_bricks_api_client.api.org import (
    org_invite_member,
    org_guest_create,
    org_guest_token_create,
    org_guest_magic_link_create,
    org_members_list_root,
)
from simbricks.client.openapi.client.python.sim_bricks_api_client.models import (
    OrgMember,
    OrgMemberList200Response,
    OrgGuestCred,
    OrgGuestMagicLinkResp,
)


class OrgClient:

    def __init__(self):
        pass

    async def get_members(self, org: str) -> OrgMemberList200Response:
        async with base_client() as client:
            members = await org_members_list_root.asyncio(org, client=client)
            members = validate_response_model(members, OrgMemberList200Response)
            assert members
            return members

    async def invite_member(self, org: str, email: str, first_name: str, last_name: str):
        invite = OrgMember(email, first_name, last_name)
        async with base_client() as client:
            await org_invite_member.asyncio(org, client=client, body=invite)

    async def create_guest(self, org: str, email: str, first_name: str, last_name: str):
        member = OrgMember(email, first_name, last_name)
        async with base_client() as client:
            await org_guest_create.asyncio(org, client=client, body=member)

    async def guest_token(self, org: str, email: str) -> Token:
        guest_cred = OrgGuestCred(email)
        async with base_client() as client:
            token = await org_guest_token_create.asyncio(org, client=client, body=guest_cred)
            return Token.parse_from_resp(token)

    async def guest_magic_link(self, org: str, email: str) -> OrgGuestMagicLinkResp:
        guest = OrgGuestCred(email)
        async with base_client() as client:
            link = org_guest_magic_link_create.asyncio(org, client=client, body=guest)
            link = validate_response_model(link, OrgGuestMagicLinkResp)
            assert link
            return link

async def org_client() -> OrgClient:
    return OrgClient()

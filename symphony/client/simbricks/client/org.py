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


from .base import base_client
from .auth import Token


class OrgClient:

    def __init__(self):
        pass

    # def _prefix(self, org: str, url: str) -> str:
    # return f"/org/{org}{url}"

    async def get_members(self, org: str):
        raise NotImplementedError()
        # async with self._base_client.get(url=self._prefix(org, f"/members")) as resp:
        #     return await resp.json()

    async def invite_member(self, org: str, email: str, first_name: str, last_name: str):
        raise NotImplementedError()
        # namespace_json = {
        #     "email": email,
        #     "first_name": first_name,
        #     "last_name": last_name,
        # }
        # async with self._base_client.post(
        #     url=self._prefix(org, "/invite-member"), json=namespace_json
        # ) as resp:
        #     await resp.json()

    async def create_guest(self, org: str, email: str, first_name: str, last_name: str):
        raise NotImplementedError()
        # namespace_json = {
        #     "email": email,
        #     "first_name": first_name,
        #     "last_name": last_name,
        # }
        # async with self._base_client.post(
        #     url=self._prefix(org, "/create-guest"), json=namespace_json
        # ) as resp:
        #     await resp.json()

    async def guest_token(self, org: str, email: str) -> Token:
        raise NotImplementedError()
        # j = {
        #     "email": email,
        # }
        # async with self._base_client.post(url=self._prefix(org, "/guest-token"), json=j) as resp:
        #     tok = await resp.json()
        #     return Token.parse_from_resp(tok)

    async def guest_magic_link(self, org: str, email: str) -> str:
        raise NotImplementedError()
        # j = {
        #     "email": email,
        # }
        # async with self._base_client.post(
        #     url=self._prefix(org, "/guest-magic-link"), json=j
        # ) as resp:
        #     return (await resp.json())["magic_link"]


def org_client() -> OrgClient:
    return OrgClient()

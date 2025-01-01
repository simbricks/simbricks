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

import json
import aiohttp
import time
import os
from .settings import client_settings


class Token:

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        session_state: str,
        access_valid_until: int,
        refresh_valid_until: int,
    ):
        self.access_token: str = access_token
        self.refresh_token: str = refresh_token
        self.session_state: str = session_state
        self.access_valid_until: int = access_valid_until
        self.refresh_valid_until: int = refresh_valid_until

    def toJSON(self) -> dict:
        return self.__dict__

    def is_access_valid(self) -> bool:
        return self.access_valid_until > int(time.time())

    def is_refresh_valid(self) -> bool:
        return self.refresh_valid_until > int(time.time())


class TokenClient:

    def __init__(
        self,
        device_auth_url: str = client_settings().auth_dev_url,
        token_url: str = client_settings().auth_token_url,
        client_id: str = client_settings().auth_client_id,
    ):
        self._device_auth_url: str = device_auth_url
        self._token_url: str = token_url
        self._client_id: str = client_id

    def _create_token_from_resp(self, json_obj) -> Token:
        access_valid_until = int(time.time()) - 10 + int(json_obj["expires_in"])
        refresh_valid_until = (
            int(time.time()) - 10 + int(json_obj["refresh_expires_in"])
        )

        return Token(
            access_token=json_obj["access_token"],
            refresh_token=json_obj["refresh_token"],
            session_state='',
            access_valid_until=access_valid_until,
            refresh_valid_until=refresh_valid_until,
        )

    async def retrieve_token(self) -> Token:

        token = None

        async with aiohttp.ClientSession() as session:

            # get device_code, interval, verification_uri, user_code
            device_code = None
            interval = None
            verification_uri = None
            user_code = None
            async with session.post(
                url=self._device_auth_url, data={"client_id": self._client_id}
            ) as resp:
                resp.raise_for_status()  # TODO: handel gracefully

                json_resp = await resp.json()
                device_code = json_resp["device_code"]
                interval = json_resp["interval"]
                verification_uri = json_resp["verification_uri"]
                user_code = json_resp["user_code"]

            assert device_code and interval and verification_uri and user_code

            # retrieve valid token upon successfull user authentication
            print(f"Please visit {verification_uri} in the browser")
            print(f"There, enter the code: {user_code}")
            print("Waiting...")
            while True:
                time.sleep(interval)  # TODO: check timeout...

                async with session.post(
                    url=self._token_url,
                    data={
                        "client_id": self._client_id,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": device_code,
                    },
                ) as resp:
                    if resp.status >= 500:
                        raise Exception(
                            f"{resp.status} error while trying toi recieve token"
                        )  # TODO: handel gracefully

                    json_resp = await resp.json()
                    if (
                        "error" in json_resp
                        and json_resp["error"] != "authorization_pending"
                    ):
                        raise Exception(
                            f"error retrievening retrieving token: {json_resp}"
                        )
                    elif "error" not in json_resp:
                        token = self._create_token_from_resp(json_obj=json_resp)
                        break

        assert token
        return token

    async def refresh_token(self, old_token: Token) -> Token:

        assert old_token.is_refresh_valid()

        token = None
        async with aiohttp.ClientSession() as session:

            # get device_code, interval, verification_uri, user_code
            async with session.post(
                url=self._token_url,
                data={
                    "client_id": self._client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": old_token.refresh_token,
                },
            ) as resp:
                resp.raise_for_status()  # TODO: handel gracefully

                json_resp = await resp.json()

                if "error" in json_resp:
                    raise Exception(f"error refreshing token: {json_resp}")

                token = self._create_token_from_resp(json_obj=json_resp)

        assert token
        return token

    async def resource_token(self, token: Token, ticket: str) -> Token:
        assert token.is_access_valid()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self._token_url,
                headers={"Authorization": f"Bearer {token.access_token}"},
                data={
                    "client_id": self._client_id,
                    "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
                    "ticket": ticket,
                },
            ) as resp:
                resp.raise_for_status()  # TODO: handel gracefully
                json_resp = await resp.json()
                if "error" in json_resp:
                    raise Exception(f"error refreshing token: {json_resp}")

                token = self._create_token_from_resp(json_obj=json_resp)

        assert token
        return token


class TokenProvider:

    def __init__(self) -> None:
        self._toke_filepath: str = "auth.json"
        self._token: Token | None = self._load_token()
        self._toke_client = TokenClient()

    def _load_token(self) -> Token | None:
        if os.path.isfile(self._toke_filepath):
            with open(self._toke_filepath) as fh:
                json_token = json.load(fh)
                return Token(
                    access_token=json_token["access_token"],
                    refresh_token=json_token["refresh_token"],
                    session_state=json_token["session_state"],
                    access_valid_until=int(json_token["access_valid_until"]),
                    refresh_valid_until=int(json_token["refresh_valid_until"]),
                )
        return None

    def _store_token(self) -> None:
        if self._token is None:
            return

        with open(self._toke_filepath, "w") as fh:
            json.dump(self._token.toJSON(), fh)

    def _access_valid(self) -> bool:
        return self._token and self._token.is_access_valid()

    def _refresh_valid(self) -> bool:
        return self._token and self._token.is_refresh_valid()

    async def _refresh_token(self) -> None:
        if self._access_valid():
            return

        if self._refresh_valid():
            assert self._token
            self._token = await self._toke_client.refresh_token(old_token=self._token)
        else:
            self._token = await self._toke_client.retrieve_token()

        assert self._token
        self._store_token()

    async def access_token(self) -> str:
        await self._refresh_token()
        assert self._token
        return self._token.access_token

    async def resource_token(self, ticket):
        await self._refresh_token()
        self._token = await self._toke_client.resource_token(self._token, ticket)
        self._store_token()
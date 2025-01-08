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

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class ClientSettings(BaseSettings):
    base_url: str = "https://app.simbricks.io/api"

    auth_client_id: str = "api.auth.simbricks.io"
    auth_token_url: str = "https://auth.simbricks.io/realms/SimBricks/protocol/openid-connect/token"
    auth_dev_url: str = "https://auth.simbricks.io/realms/SimBricks/protocol/openid-connect/auth/device"

    namespace: str = ""
    runner_id: int = -1

@lru_cache
def client_settings() -> ClientSettings:
    return ClientSettings(_env_file="internal.env", _env_file_encoding="utf-8")
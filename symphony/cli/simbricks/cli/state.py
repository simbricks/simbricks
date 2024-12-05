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

import os
from simbricks.client import BaseClient, AdminClient, NSClient, SimBricksClient


class State:
    def __init__(self):
        self.namespace = ""
        self._base_client: BaseClient | None = None
        self._admin_client: AdminClient = None
        self._ns_client: NSClient | None = None
        self._simbricks_client: SimBricksClient | None = None

    @property
    def base_client(self):
        if self._base_client is None:
            self._base_client = BaseClient()
        return self._base_client

    @property
    def admin_client(self):
        if self._admin_client is None:
            self._admin_client = AdminClient(base_client=self.base_client)
        return self._admin_client

    @property
    def ns_client(self):
        if self._ns_client is None:
            self._ns_client = NSClient(base_client=self.base_client, namespace=self.namespace)
        return self._ns_client

    @property
    def simbricks_client(self):
        if self._simbricks_client is None:
            self._simbricks_client = SimBricksClient(self.ns_client)
        return self._simbricks_client


state = State()

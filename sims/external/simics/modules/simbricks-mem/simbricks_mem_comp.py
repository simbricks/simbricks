# SimBricks Memory Adapter Component
#
# Copyright (c) 2020-2023 Max Planck Institute for Software Systems
# Copyright (c) 2020-2023 National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import simics
from comp import SimpleConfigAttribute, StandardComponent


class simbricks_mem_comp(StandardComponent):
    """SimBricks memory adapter component."""

    def setup(self):
        super().setup()
        if not self.instantiated.val:
            self.add_objects()

    def add_objects(self):
        simbricks_mem_dev = self.add_pre_obj(
            'simbricks_mem_dev', 'simbricks_mem'
        )
        simbricks_mem_dev.socket = self.socket.val
        simbricks_mem_dev.mem_latency = self.mem_latency.val
        simbricks_mem_dev.sync_period = self.sync_period.val
        if self.cache_size.val is not None:
            simbricks_mem_dev.cache_size = self.cache_size.val
        if self.cache_line_size.val is not None:
            simbricks_mem_dev.cache_line_size = self.cache_line_size.val

    class basename(StandardComponent.basename):
        """The default name for the created component."""
        val = 'simbricks_mem_comp'

    class socket(SimpleConfigAttribute(None, 's', simics.Sim_Attr_Required)):
        """Socket Path for SimBricks messages."""

    class mem_latency(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Required)
    ):
        """Latency in nanoseconds from host to memory."""

    class sync_period(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Required)
    ):
        """Period for sending SimBricks synchronization messages in
        nanoseconds."""

    class cache_size(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Optional)
    ):
        """Number of cache lines."""

    class cache_line_size(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Optional)
    ):
        """Size of each cache line in bytes."""

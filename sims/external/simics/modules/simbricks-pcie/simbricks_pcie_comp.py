# SimBricks PCIe Adapter Component
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
from comp import StandardComponent, SimpleConfigAttribute, Interface


class simbricks_pcie_comp(StandardComponent):
    """SimBricks PCIe adapter device."""
    _class_desc = 'SimBricks PCIe adapter device'
    _help_categories = ('PCI',)

    def setup(self):
        super().setup()
        if not self.instantiated.val:
            self.add_objects()
        self.add_connectors()

    def add_objects(self):
        simbricks_pcie_dev = self.add_pre_obj(
            'simbricks_pcie_dev', 'simbricks_pcie'
        )
        simbricks_pcie_dev.socket = self.socket.val
        simbricks_pcie_dev.pci_latency = self.pci_latency.val
        simbricks_pcie_dev.sync_period = self.sync_period.val

    def add_connectors(self):
        self.add_connector(
            slot='pci_bus',
            type='pci-bus',
            hotpluggable=True,
            required=True,
            multi=False,
            direction=simics.Sim_Connector_Direction_Up
        )

    class basename(StandardComponent.basename):
        """The default name for the created component."""
        val = 'simbricks_pcie'

    class socket(SimpleConfigAttribute(None, 's', simics.Sim_Attr_Required)):
        """Socket Path for SimBricks messages."""

    class pci_latency(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Required)
    ):
        """PCI Latency in nanoseconds from host to device."""

    class sync_period(
        SimpleConfigAttribute(None, 'i', simics.Sim_Attr_Required)
    ):
        """Period for sending SimBricks synchronization messages in
        nanoseconds."""

    class component_connector(Interface):
        """Uses connector for handling connections between components."""

        def get_check_data(self, cnt):
            return []

        def get_connect_data(self, cnt):
            return [[[0, self._up.get_slot('simbricks_pcie_dev')]]]

        def check(self, cnt, attr):
            return True

        def connect(self, cnt, attr):
            self._up.get_slot('simbricks_pcie_dev').pci_bus = attr[1]

        def disconnect(self, cnt):
            self._up.get_slot('simbricks_pcie_dev').pci_bus = None

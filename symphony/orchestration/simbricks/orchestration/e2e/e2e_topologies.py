# Copyright 2023 Max Planck Institute for Software Systems, and
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

# Allow own class to be used as type for a method's argument
from __future__ import annotations

from abc import ABC, abstractmethod

import simbricks.orchestration.e2e_components as e2e


class E2ETopology(ABC):

    @abstractmethod
    def add_to_network(self, net):
        pass


class E2EDumbbellTopology(E2ETopology):

    def __init__(self):
        self.left_switch = e2e.E2ESwitchNode('_leftSwitch')
        self.right_switch = e2e.E2ESwitchNode('_rightSwitch')
        self.link = e2e.E2ESimpleChannel('_link')
        self.link.left_node = self.left_switch
        self.link.right_node = self.right_switch

    def add_to_network(self, net):
        net.add_component(self.left_switch)
        net.add_component(self.right_switch)
        net.add_component(self.link)

    def add_left_component(self, component: e2e.E2EComponent):
        self.left_switch.add_component(component)

    def add_right_component(self, component: e2e.E2EComponent):
        self.right_switch.add_component(component)

    @property
    def mtu(self):
        return self.left_switch.mtu

    @mtu.setter
    def mtu(self, mtu: str):
        self.left_switch.mtu = mtu
        self.right_switch.mtu = mtu

    @property
    def data_rate(self):
        return self.link.data_rate

    @data_rate.setter
    def data_rate(self, data_rate: str):
        self.link.data_rate = data_rate

    @property
    def queue_size(self):
        return self.link.queue_size

    @queue_size.setter
    def queue_size(self, queue_size: str):
        self.link.queue_size = queue_size

    @property
    def delay(self):
        return self.link.delay

    @delay.setter
    def delay(self, delay: str):
        self.link.delay = delay

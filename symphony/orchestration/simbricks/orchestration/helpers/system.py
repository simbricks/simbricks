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


from simbricks.orchestration import system
from simbricks.orchestration.utils import base as utils_base


def connect_host_and_device(
    host: system.Host, device: system.Component
) -> system.pcie.PCIeChannel:
    utils_base.has_expected_type(obj=host, expected_type=system.Host)
    utils_base.has_expected_type(obj=device, expected_type=system.Component)

    host_interface = system.pcie.PCIeHostInterface(c=host)
    host.add_if(interface=host_interface)

    device_interface = system.pcie.PCIeDeviceInterface(c=device)
    device.add_if(interface=device_interface)

    pcie_channel = system.pcie.PCIeChannel(host=host_interface, dev=device_interface)
    return pcie_channel


def connect_eth_devices(
    device_a: system.Component, device_b: system.Component
) -> system.EthChannel:
    utils_base.has_expected_type(obj=device_a, expected_type=system.Component)
    utils_base.has_expected_type(obj=device_b, expected_type=system.Component)

    eth_inter_a = system.eth.EthInterface(c=device_a)
    device_a.add_if(interface=eth_inter_a)

    eth_inter_b = system.eth.EthInterface(c=device_b)
    device_b.add_if(interface=eth_inter_b)

    eth_channel = system.eth.EthChannel(a=eth_inter_a, b=eth_inter_b)
    return eth_channel


def install_app(
    host: system.Host, app_ty: system.Application, **kwargs
) -> system.Application:
    utils_base.has_expected_type(obj=host, expected_type=system.Host)
    utils_base.has_expected_type(obj=app_ty, expected_type=system.Application)

    application = app_ty(h=host, **kwargs)
    host.add_app(a=application)

    return application

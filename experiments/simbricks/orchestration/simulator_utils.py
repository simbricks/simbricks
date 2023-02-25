# Copyright 2021 Max Planck Institute for Software Systems, and
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
"""Provides helper functions for assembling multiple host simulators."""

import typing as tp

from simbricks.orchestration.experiments import Experiment
from simbricks.orchestration.nodeconfig import AppConfig, NodeConfig
from simbricks.orchestration.simulators import (
    HostSim, I40eMultiNIC, NetSim, NICSim
)


def create_basic_hosts(
    e: Experiment,
    num: int,
    name_prefix: str,
    net: NetSim,
    nic_class: tp.Type[NICSim],
    host_class: tp.Type[HostSim],
    nc_class: tp.Type[NodeConfig],
    app_class: tp.Type[AppConfig],
    ip_start: int = 1,
    ip_prefix: int = 24
) -> tp.List[HostSim]:
    """
    Creates and configures multiple hosts to be simulated using the given
    parameters.

    Args:
        num: number of hosts to create
    """

    hosts: tp.List[HostSim] = []
    for i in range(0, num):
        nic = nic_class()
        #nic.name = '%s.%d' % (name_prefix, i)
        nic.set_network(net)

        node_config = nc_class()
        node_config.prefix = ip_prefix
        ip = ip_start + i
        node_config.ip = f'10.0.{int(ip / 256)}.{ip % 256}'
        node_config.app = app_class()

        host = host_class(node_config)
        host.name = f'{name_prefix}.{i}'

        host.add_nic(nic)
        e.add_nic(nic)
        e.add_host(host)

        hosts.append(host)

    return hosts


def create_multinic_hosts(
    e: Experiment,
    num: int,
    name_prefix: str,
    net: NetSim,
    host_class: tp.Type[HostSim],
    nc_class: tp.Type[NodeConfig],
    app_class: tp.Type[AppConfig],
    ip_start: int = 1,
    ip_prefix: int = 24
) -> tp.List[HostSim]:
    """
    Creates and configures multiple hosts to be simulated using the given
    parameters. These hosts use multiple NICs.

    Args:
        num: number of hosts to create
    """

    hosts: tp.List[HostSim] = []

    mn = I40eMultiNIC()
    mn.name = name_prefix
    e.add_nic(mn)

    for i in range(0, num):
        nic = mn.create_subnic()
        #nic.name = '%s.%d' % (name_prefix, i)
        nic.set_network(net)

        node_config = nc_class()
        node_config.prefix = ip_prefix
        ip = ip_start + i
        node_config.ip = f'10.0.{int(ip / 256)}.{ip % 256}'
        node_config.app = app_class()

        host = host_class(node_config)
        host.name = f'{name_prefix}.{i}'

        host.add_nic(nic)
        e.add_host(host)

        hosts.append(host)

    return hosts


def create_dctcp_hosts(
    e: Experiment,
    num: int,
    name_prefix: str,
    net: NetSim,
    nic_class: tp.Type[NICSim],
    host_class: tp.Type[HostSim],
    nc_class: tp.Type[NodeConfig],
    app_class: tp.Type[AppConfig],
    cpu_freq: str,
    mtu: int,
    ip_start: int = 1
) -> tp.List[HostSim]:
    """
    Creates and configures multiple hosts to be simulated in a DCTCP experiment
    using the given parameters.

    Args:
        num: number of hosts to create
        cpu_freq: CPU frequency to simulate, e.g. '5GHz'
    """
    hosts = []
    for i in range(0, num):
        nic = nic_class()
        #nic.name = '%s.%d' % (name_prefix, i)
        nic.set_network(net)

        node_config = nc_class()
        node_config.mtu = mtu
        node_config.ip = f'192.168.64.{ip_start + i}'
        node_config.app = app_class()

        host = host_class(node_config)
        host.name = f'{name_prefix}.{i}'
        host.cpu_freq = cpu_freq

        host.add_nic(nic)
        e.add_nic(nic)
        e.add_host(host)

        hosts.append(host)

    return hosts


def create_tcp_cong_hosts(
    e: Experiment,
    num: int,
    name_prefix: str,
    net: NetSim,
    nic_class: tp.Type[NICSim],
    host_class: tp.Type[HostSim],
    nc_class: tp.Type[NodeConfig],
    app_class: tp.Type[AppConfig],
    cpu_freq: str,
    mtu: int,
    congestion_control: str,
    ip_start: int = 1
):
    """
    Creates and configures multiple hosts to be simulated in a TCP congestion
    control experiment using the given parameters.

    Args:
        num: number of hosts to create
        cpu_freq: CPU frequency to simulate, e.g. '5GHz'
    """
    hosts = []
    for i in range(0, num):
        nic = nic_class()
        #nic.name = '%s.%d' % (name_prefix, i)
        nic.set_network(net)

        node_config = nc_class()
        node_config.mtu = mtu
        node_config.tcp_congestion_control = congestion_control
        node_config.ip = f'192.168.64.{ip_start + i}'
        node_config.app = app_class()

        host = host_class(node_config)
        host.name = f'{name_prefix}.{i}'
        host.cpu_freq = cpu_freq

        host.add_nic(nic)
        e.add_nic(nic)
        e.add_host(host)

        hosts.append(host)

    return hosts

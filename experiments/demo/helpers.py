from simbricks.orchestration import system
import re

"""
Helper functions that are used within the other files in this folder.
"""

# Custom defined helper function to create an 'I40ELinuxHost' attached to an 'IntelI40eNIC'.
def sys_host_nic(sys, image, ip, hn=None, nn=None):
    host = system.I40ELinuxHost(sys)
    host.add_disk(image)
    host.add_disk(system.LinuxConfigDiskImage(sys, host))
    if hn:
        host.name = hn

    nic = system.IntelI40eNIC(sys)
    nic.add_ipv4(ip)
    host.connect_pcie_dev(nic)
    if nn:
        nic.name = nn

    return host, nic


def parse_Iperf_line_bytes(line: str) -> float | None:
    pattern = r"(\d+\.?\d*)\s*MBytes"
    match = re.search(pattern, line)
    if not match:
        return None
    m_bytes = float(match.group(1))
    return m_bytes

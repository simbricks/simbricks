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

import tarfile
import io
import pathlib

class NodeConfig(object):
    sim = 'qemu'
    ip = '10.0.0.1'
    prefix = 24
    cores = 1
    memory = 8 * 1024
    disk_image = 'base'
    app = None
    mtu = 1500

    def config_str(self):
        if self.sim == 'qemu':
            cp_es = []
            exit_es = ['poweroff -f']
        else:
            cp_es = ['m5 checkpoint']
            exit_es = ['m5 exit']

        es = self.prepare_pre_cp() + self.app.prepare_pre_cp() + cp_es + \
            self.prepare_post_cp() + self.app.prepare_post_cp() + \
            self.run_cmds() + self.cleanup_cmds() + exit_es
        return '\n'.join(es)

    def make_tar(self, path):
        tar = tarfile.open(path, 'w:')

        # add main run script
        cfg_i = tarfile.TarInfo('guest/run.sh')
        cfg_i.mode = 0o777
        cfg_f = self.strfile(self.config_str())
        cfg_f.seek(0, io.SEEK_END)
        cfg_i.size = cfg_f.tell()
        cfg_f.seek(0, io.SEEK_SET)
        tar.addfile(tarinfo=cfg_i, fileobj=cfg_f)
        cfg_f.close()

        # add additional config files
        for (n,f) in self.config_files().items():
            f_i = tarfile.TarInfo('guest/' + n)
            f_i.mode = 0o777
            f.seek(0, io.SEEK_END)
            f_i.size = f.tell()
            f.seek(0, io.SEEK_SET)
            tar.addfile(tarinfo=f_i, fileobj=f)
            f.close()

        tar.close()

    def prepare_pre_cp(self):
        return [
            'set -x',
            'export HOME=/root',
            'export LANG=en_US',
            'export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:' + \
                '/usr/bin:/sbin:/bin:/usr/games:/usr/local/games"'
        ]

    def prepare_post_cp(self):
        return []

    def run_cmds(self):
        return self.app.run_cmds(self)

    def cleanup_cmds(self):
        return []

    def config_files(self):
        return self.app.config_files()

    def strfile(self, s):
        return io.BytesIO(bytes(s, encoding='UTF-8'))


class AppConfig(object):
    def run_cmds(self, node):
        return []

    def prepare_pre_cp(self):
        return []

    def prepare_post_cp(self):
        return []

    def config_files(self):
        return {}

    def strfile(self, s):
        return io.BytesIO(bytes(s, encoding='UTF-8'))


class LinuxNode(NodeConfig):
    ifname = 'eth0'

    def __init__(self):
        self.drivers = []

    def prepare_post_cp(self):
        l = []
        for d in self.drivers:
            if d[0] == '/':
                l.append('insmod ' + d)
            else:
                l.append('modprobe ' + d)
        l.append('ip link set dev ' + self.ifname + ' up')
        l.append('ip addr add %s/%d dev %s' %
                (self.ip, self.prefix, self.ifname))
        return super().prepare_post_cp() + l

class I40eLinuxNode(LinuxNode):
    def __init__(self):
        super().__init__()
        self.drivers.append('i40e')

class CorundumLinuxNode(LinuxNode):
    def __init__(self):
        super().__init__()
        self.drivers.append('/tmp/guest/mqnic.ko')

    def config_files(self):
        m = {'mqnic.ko': open('../images/mqnic/mqnic.ko', 'rb')}
        return {**m, **super().config_files()}



class MtcpNode(NodeConfig):
    disk_image = 'mtcp'
    pci_dev = '0000:00:02.0'
    memory = 16 * 1024
    num_hugepages = 4096

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'mkdir -p /dev/hugepages',
            'mount -t hugetlbfs nodev /dev/hugepages',
            'mkdir -p /dev/shm',
            'mount -t tmpfs tmpfs /dev/shm',
            'echo ' + str(self.num_hugepages) + ' > /sys/devices/system/' + \
                    'node/node0/hugepages/hugepages-2048kB/nr_hugepages',
        ]

    def prepare_post_cp(self):
        return super().prepare_post_cp() + [
            'insmod /root/mtcp/dpdk/x86_64-native-linuxapp-gcc/kmod/igb_uio.ko',
            '/root/mtcp/dpdk/usertools/dpdk-devbind.py -b igb_uio ' +
                self.pci_dev,
            'insmod /root/mtcp/dpdk-iface-kmod/dpdk_iface.ko',
            '/root/mtcp/dpdk-iface-kmod/dpdk_iface_main',
            'ip link set dev dpdk0 up',
            'ip addr add %s/%d dev dpdk0' % (self.ip, self.prefix)
        ]

    def config_files(self):
        m = {'mtcp.conf': self.strfile("io = dpdk\n"
                "num_cores = " + str(self.cores) + "\n"
                "num_mem_ch = 4\n"
                "port = dpdk0\n"
                "max_concurrency = 4096\n"
                "max_num_buffers = 4096\n"
                "rcvbuf = 8192\n"
                "sndbuf = 8192\n"
                "tcp_timeout = 10\n"
                "tcp_timewait = 0\n"
                "#stat_print = dpdk0\n")}

        return {**m, **super().config_files()}

class TASNode(NodeConfig):
    disk_image = 'tas'
    pci_dev = '0000:00:02.0'
    memory = 16 * 1024
    num_hugepages = 4096
    fp_cores = 1
    preload = True

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'mkdir -p /dev/hugepages',
            'mount -t hugetlbfs nodev /dev/hugepages',
            'mkdir -p /dev/shm',
            'mount -t tmpfs tmpfs /dev/shm',
            'echo ' + str(self.num_hugepages) + ' > /sys/devices/system/' + \
                    'node/node0/hugepages/hugepages-2048kB/nr_hugepages',
        ]

    def prepare_post_cp(self):
        cmds = super().prepare_post_cp() + [
            'insmod /root/dpdk/lib/modules/5.4.46/extra/dpdk/igb_uio.ko',
            '/root/dpdk/sbin/dpdk-devbind -b igb_uio ' + self.pci_dev,
            'cd /root/tas',
            'tas/tas --ip-addr=%s/%d --fp-cores-max=%d --fp-no-ints &' % (
                self.ip, self.prefix, self.fp_cores),
            'sleep 1'
        ]

        if self.preload:
             cmds += ['export LD_PRELOAD=/root/tas/lib/libtas_interpose.so']
        return cmds



class I40eDCTCPNode(NodeConfig):
    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'sysctl -w net.core.rmem_default=31457280',
            'sysctl -w net.core.rmem_max=31457280',
            'sysctl -w net.core.wmem_default=31457280',
            'sysctl -w net.core.wmem_max=31457280',
            'sysctl -w net.core.optmem_max=25165824',
            'sysctl -w net.ipv4.tcp_mem="786432 1048576 26777216"',
            'sysctl -w net.ipv4.tcp_rmem="8192 87380 33554432"',
            'sysctl -w net.ipv4.tcp_wmem="8192 87380 33554432"',
            'sysctl -w net.ipv4.tcp_congestion_control=dctcp',
            'sysctl -w net.ipv4.tcp_ecn=1'
        ]


    def prepare_post_cp(self):
        return super().prepare_post_cp() + [
            'modprobe i40e',
            'ethtool -G eth0 rx 4096 tx 4096',
            'ethtool -K eth0 tso off',
            'ip link set eth0 txqueuelen 13888',
            f'ip link set dev eth0 mtu {self.mtu} up',
            f'ip addr add {self.ip}/{self.prefix} dev eth0',
        ]

class CorundumDCTCPNode(NodeConfig):
    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'sysctl -w net.core.rmem_default=31457280',
            'sysctl -w net.core.rmem_max=31457280',
            'sysctl -w net.core.wmem_default=31457280',
            'sysctl -w net.core.wmem_max=31457280',
            'sysctl -w net.core.optmem_max=25165824',
            'sysctl -w net.ipv4.tcp_mem="786432 1048576 26777216"',
            'sysctl -w net.ipv4.tcp_rmem="8192 87380 33554432"',
            'sysctl -w net.ipv4.tcp_wmem="8192 87380 33554432"',
            'sysctl -w net.ipv4.tcp_congestion_control=dctcp',
            'sysctl -w net.ipv4.tcp_ecn=1'
        ]


    def prepare_post_cp(self):
        return super().prepare_post_cp() + [
            'insmod mqnic.ko',
            'ip link set dev eth0 up',
            f'ip addr add {self.ip}/{self.prefix} dev eth0',
        ]


class LinuxFEMUNode(NodeConfig):
    def __init__(self):
        self.drivers = ['nvme']

    def prepare_post_cp(self):
        l = ['lspci -vvvv']
        for d in self.drivers:
            if d[0] == '/':
                l.append('insmod ' + d)
            else:
                l.append('modprobe ' + d)
        return super().prepare_post_cp() + l

class NVMEFsTest(AppConfig):
    def run_cmds(self, node):
        return ['mount -t proc proc /proc',
                'mkfs.ext3 /dev/nvme0n1',
                'mount /dev/nvme0n1 /mnt',
                'dd if=/dev/urandom of=/mnt/foo bs=1024 count=1024']

class DctcpServer(AppConfig):
    def run_cmds(self, node):
        return ['iperf -s -w 1M -Z dctcp']

class DctcpClient(AppConfig):
    server_ip = '192.168.64.1'
    is_last = False
    def run_cmds(self, node):
        if (self.is_last):
            return ['sleep 1',
                    f'iperf -w 1M -c {self.server_ip} -Z dctcp -i 1',
                    'sleep 2'
                    ]
        else:
            return ['sleep 1',
                    f'iperf -w 1M -c {self.server_ip} -Z dctcp -i 1',
                    'sleep 20'
                    ]

class PingClient(AppConfig):
    server_ip = '192.168.64.1'

    def run_cmds(self, node):
        return [f'ping {self.server_ip} -c 100']

class IperfTCPServer(AppConfig):
    def run_cmds(self, node):
        return ['iperf -s -l 32M -w 32M']

class IperfUDPServer(AppConfig):
    def run_cmds(self, node):
        return ['iperf -s -u']

class IperfTCPClient(AppConfig):
    server_ip = '10.0.0.1'
    procs = 1
    is_last = False

    def run_cmds(self, node):

        cmds = ['sleep 1',
                'iperf -l 32M -w 32M  -c ' + self.server_ip + ' -i 1 -P ' +
                str(self.procs)]
        if self.is_last:
            cmds.append('sleep 0.5')
        else:
            cmds.append('sleep 10')
        return cmds

class IperfUDPClient(AppConfig):
    server_ip = '10.0.0.1'
    rate = '150m'
    is_last = False

    def run_cmds(self, node):
        cmds = ['sleep 1',
                'iperf -c ' + self.server_ip + ' -i 1 -u -b ' + self.rate]

        if self.is_last:
            cmds.append('sleep 0.5')
        else:
            cmds.append('sleep 10')

        return cmds



class IperfUDPClientSleep(AppConfig):
    server_ip = '10.0.0.1'
    rate = '150m'
    def run_cmds(self, node):
        return ['sleep 1',
                'sleep 10'
                ]


class NoTraffic(AppConfig):
    is_sleep = 1
    is_server = 0
    def run_cmds(self, node):
        cmds = []
        if (self.is_server):
            cmds.append('sleep infinity')
        else:
            if (self.is_sleep):
                cmds.append('sleep 10')

            else:
                cmds.append('dd if=/dev/urandom of=/dev/null count=500000')

        return cmds

class NetperfServer(AppConfig):
    def run_cmds(self, node):
        return ['netserver',
                'sleep infinity']

class NetperfClient(AppConfig):
    server_ip = '10.0.0.1'
    def run_cmds(self, node):
        return ['netserver', 'sleep 0.5',
                'netperf -H ' + self.server_ip,
                'netperf -H ' + self.server_ip + ' -t TCP_RR -- -o mean_latency,p50_latency,p90_latency,p99_latency']

class VRReplica(AppConfig):
    index = 0
    def run_cmds(self, node):
        return ['/root/nopaxos/bench/replica -c /root/nopaxos.config -i ' +
                str(self.index) + ' -m vr']

class VRClient(AppConfig):
    server_ips = []
    def run_cmds(self, node):
        cmds = []
        for ip in self.server_ips:
            cmds.append('ping -c 2 ' + ip)
        cmds.append('/root/nopaxos/bench/client -c /root/nopaxos.config ' +
                '-m vr -u 2 -h ' + node.ip)
        return cmds

class NOPaxosReplica(AppConfig):
    index = 0
    def run_cmds(self, node):
        return ['/root/nopaxos/bench/replica -c /root/nopaxos.config -i ' +
                str(self.index) + ' -m nopaxos']

class NOPaxosClient(AppConfig):
    server_ips = []
    is_last = False
    use_ehseq = False

    def run_cmds(self, node):
        cmds = []
        for ip in self.server_ips:
            cmds.append('ping -c 2 ' + ip)
        cmd = '/root/nopaxos/bench/client -c /root/nopaxos.config ' + \
                '-m nopaxos -u 2 -h ' + node.ip
        if self.use_ehseq:
            cmd += ' -e'
        cmds.append(cmd)
        if self.is_last:
            cmds.append('sleep 1')
        else:
            cmds.append('sleep infinity')
        return cmds

class NOPaxosSequencer(AppConfig):
    def run_cmds(self, node):
        return ['/root/nopaxos/sequencer/sequencer -c /root/nopaxos.config -m nopaxos']


class RPCServer(AppConfig):
    port = 1234
    threads = 1
    max_flows = 1234
    max_bytes = 1024

    def run_cmds(self, node):
        exe = 'echoserver_linux' if not isinstance(node, MtcpNode) else \
            'echoserver_mtcp'
        return ['cd /root/tasbench/micro_rpc',
            './%s %d %d /tmp/guest/mtcp.conf %d %d' % (exe, self.port,
                self.threads, self.max_flows, self.max_bytes)]

class RPCClient(AppConfig):
    server_ip = '10.0.0.1'
    port = 1234
    threads = 1
    max_flows = 128
    max_bytes = 1024
    max_pending = 1
    openall_delay = 2
    max_msgs_conn = 0
    max_pend_conns = 8
    time = 25

    def run_cmds(self, node):
        exe = 'testclient_linux' if not isinstance(node, MtcpNode) else \
            'testclient_mtcp'
        return ['cd /root/tasbench/micro_rpc',
            './%s %s %d %d /tmp/guest/mtcp.conf %d %d %d %d %d %d &' % (exe,
                self.server_ip, self.port, self.threads, self.max_bytes,
                self.max_pending, self.max_flows, self.openall_delay,
                self.max_msgs_conn, self.max_pend_conns),
            'sleep %d' % (self.time)]


################################################################################

class HTTPD(AppConfig):
    threads = 1
    file_size = 64
    mtcp_config = 'lighttpd.conf'

    def prepare_pre_cp(self):
        return ['mkdir -p /srv/www/htdocs/ /tmp/lighttpd/',
            'dd if=/dev/zero of=/srv/www/htdocs/file bs=%d count=1' % \
                (self.file_size)]

    def run_cmds(self, node):
        return ['cd %s/src/' % (self.httpd_dir),
            './lighttpd -D -f ../doc/config/%s -n %d -m ./.libs/' % \
                (self.mtcp_config, self.threads)]

class HTTPDLinux(HTTPD):
    httpd_dir = '/root/mtcp/apps/lighttpd-mtlinux'

class HTTPDLinuxRPO(HTTPD):
    httpd_dir = '/root/mtcp/apps/lighttpd-mtlinux-rop'

class HTTPDMtcp(HTTPD):
    httpd_dir = '/root/mtcp/apps/lighttpd-mtcp'
    mtcp_config = 'm-lighttpd.conf'

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'cp /tmp/guest/mtcp.conf %s/src/mtcp.conf' % (self.httpd_dir),
            'sed -i "s:^server.document-root =.*:server.document-root = server_root + \\"/htdocs\\":" %s' % \
                    (self.httpd_dir + '/doc/config/' + self.mtcp_config)
        ]


class HTTPC(AppConfig):
    server_ip = '10.0.0.1'
    conns = 1000
    #requests = 10000000
    requests = 10000
    threads = 1
    url = '/file'

    def run_cmds(self, node):
        return ['cd %s/support/' % (self.ab_dir),
            './ab -N %d -c %d -n %d %s%s' % \
                (self.threads, self.conns, self.requests, self.server_ip,
                    self.url)]

class HTTPCLinux(HTTPC):
    ab_dir = '/root/mtcp/apps/ab-linux'

class HTTPCMtcp(HTTPC):
    ab_dir = '/root/mtcp/apps/ab-mtcp'

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'cp /tmp/guest/mtcp.conf %s/support/config/mtcp.conf' % \
                    (self.ab_dir),
            'rm -f %s/support/config/arp.conf' % (self.ab_dir)
        ]


class MemcachedServer(AppConfig):
    def run_cmds(self, node):
        return ['memcached -u root -t 1 -c 4096']

class MemcachedClient(AppConfig):
    server_ips = ['10.0.0.1']
    threads = 1
    concurrency = 1
    throughput = '1k'
    def run_cmds(self, node):
        servers = [ip + ':11211' for ip in self.server_ips]
        servers = ','.join(servers)
        return [f'memaslap --binary --time 10s --server={servers} --thread={self.threads} --concurrency={self.concurrency} --tps={self.throughput} --verbose']

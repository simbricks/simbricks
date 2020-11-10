import tarfile
import io
import pathlib

class NodeConfig(object):
    sim = 'qemu'
    ip = '10.0.0.1'
    prefix = 24
    cores = 1
    memory = 512
    app = None

    def config_str(self):
        if self.sim == 'qemu':
            cp_es = []
            exit_es = ['poweroff -f']
        else:
            cp_es = ['m5 checkpoint']
            exit_es = ['m5 exit']

        es = self.prepare_pre_cp() + cp_es + self.prepare_post_cp() + \
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
        return {}

    def strfile(self, s):
        return io.BytesIO(bytes(s, encoding='UTF-8'))


class AppConfig(object):
    def run_cmds(self, node):
        return []


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
        m = {'mqnic.ko': open('../images/mqnic/mqnic.ko', 'r')}
        return {**m, **super().config_files()}



class MtcpNode(NodeConfig):
    pci_dev = '0000:00:02.0'
    num_hugepages = 4096

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'mkdir -p /dev/hugepages',
            'mount -t hugetlbfs nodev /dev/hugepages',
            'mkdir -p /dev/shm',
            'mount -t tmpfs tmpfs /dev/shm'
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
                "stat_print = dpdk0\n")}

        return {**m, **super().config_files()}

class TASNode(NodeConfig):
    pci_dev = '0000:00:02.0'
    num_hugepages = 4096

    def prepare_pre_cp(self):
        return super().prepare_pre_cp() + [
            'mount -t proc proc /proc',
            'mount -t sysfs sysfs /sys',
            'mkdir -p /dev/hugepages',
            'mount -t hugetlbfs nodev /dev/hugepages',
            'mkdir -p /dev/shm',
            'mount -t tmpfs tmpfs /dev/shm'
            'echo ' + str(self.num_hugepages) + ' > /sys/devices/system/' + \
                    'node/node0/hugepages/hugepages-2048kB/nr_hugepages',
        ]

    def prepare_post_cp(self):
        return super().prepare_post_cp() + [
            'insmod /root/dpdk/lib/modules/5.4.46/extra/dpdk/igb_uio.ko',
            '/root/mtcp/dpdk/usertools/dpdk-devbind.py -b igb_uio ' +
                self.pci_dev,
            'insmod /root/mtcp/dpdk-iface-kmod/dpdk_iface.ko',
            '/root/mtcp/dpdk-iface-kmod/dpdk_iface_main',
            'ip link set dev dpdk0 up',
            'ip addr add %s/%d dev dpdk0' % (self.ip, self.prefix)
        ]


class IperfTCPServer(AppConfig):
    def run_cmds(self, node):
        return ['iperf -s -l 32M -w 32M']

class IperfUDPServer(AppConfig):
    def run_cmds(self, node):
        return ['iperf -s -u']

class IperfTCPClient(AppConfig):
    server_ip = '10.0.0.1'
    procs = 1

    def run_cmds(self, node):
        return ['iperf -l 32M -w 32M  -c ' + self.server_ip +  ' -i 1 -P ' +
                str(self.procs)]

class IperfUDPClient(AppConfig):
    server_ip = '10.0.0.1'
    rate = '150m'
    def run_cmds(self, node):
        return ['iperf -c ' + self.server_ip + ' -u -b ' + self.rate]

class NOPaxosReplica(AppConfig):
    index = 0
    def run_cmds(self, node):
        return ['/root/nopaxos/bench/replica -c /root/nopaxos.config -i ' +
                str(self.index) + ' -m nopaxos']

class NOPaxosClient(AppConfig):
    def run_cmds(self, node):
        return ['/root/nopaxos/bench/client -c /root/nopaxos.config ' +
                '-m nopaxos -n 2000']

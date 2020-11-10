class Simulator(object):
    # number of cores required for this simulator
    def resreq_cores(self):
        return 1

    # memory required for this simulator (in MB)
    def resreq_mem(self):
        return 64

    def prep_cmds(self, env):
        return []

    def run_cmd(self, env):
        pass

class HostSim(Simulator):
    node_config = None
    disk_image = 'base'
    name = ''
    wait = False

    def __init__(self):
        self.nics = []

    def full_name(self):
        return 'host.' + self.name

    def add_nic(self, nic):
        nic.name = self.name + '.' + nic.name
        self.nics.append(nic)

    def set_config(self, nc):
        self.node_config = nc

class NICSim(Simulator):
    network = None
    name = ''

    def set_network(self, net):
        self.network = net
        net.nics.append(self)

    def basic_run_cmd(self, env, name):
        return '%s/%s %s %s %s' % \
            (env.repodir, name, env.nic_pci_path(self), env.nic_eth_path(self),
                    env.nic_shm_path(self))

    def full_name(self):
        return 'nic.' + self.name

class NetSim(Simulator):
    name = ''
    opt = ''

    def __init__(self):
        self.nics = []

    def full_name(self):
        return 'net.' + self.name


class QemuHost(HostSim):
    mem = 16 * 1024 # 16G

    def resreq_cores(self):
        return self.node_config.cores + 1

    def resreq_mem(self):
        return 4096

    def prep_cmds(self, env):
        to_path = env.hdcopy_path(self)
        return [f'{env.qemu_img_path} create -f qcow2 -o '
            f'backing_file="{env.hd_path(self.disk_image)}" '
            f'{env.hdcopy_path(self)}']

    def run_cmd(self, env):
        cmd = (f'{env.qemu_path} -machine q35 -cpu host -serial mon:stdio '
            '-display none -enable-kvm -nic none '
            f'-kernel {env.qemu_kernel_path} '
            f'-drive file={env.hdcopy_path(self)},if=ide,index=0,media=disk '
            f'-drive file={env.cfgtar_path(self)},if=ide,index=1,media=disk,'
                'driver=raw '
            '-append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 '
                'init=/home/ubuntu/guestinit.sh rw" '
            f'-m {self.mem} -smp {self.node_config.cores} ')
        if len(self.nics) > 0:
            assert len(self.nics) == 1
            cmd += f'-chardev socket,path={env.nic_pci_path(self.nics[0])},'
            cmd += 'id=cosimcd '
            cmd += '-device cosim-pci,chardev=cosimcd '
        return cmd

class Gem5Host(HostSim):
    mem = 16 * 1024 # 16G
    cpu_type_cp = 'X86KvmCPU'
    cpu_type = 'TimingSimpleCPU'

    def set_config(self, nc):
        nc.sim = 'gem5'
        super().set_config(nc)

    def resreq_cores(self):
        return 1

    def resreq_mem(self):
        return 4096

    def prep_cmds(self, env):
        return [f'mkdir -p {env.gem5_cpdir(self)}']

    def run_cmd(self, env):
        cpu_type = self.cpu_type
        if env.create_cp:
            cpu_type = self.cpu_type_cp

        cmd = (f'{env.gem5_path} --outdir={env.gem5_outdir(self)} '
            f'{env.gem5_py_path} --caches --l2cache --l3cache '
            '--l1d_size=32kB --l1i_size=32kB --l2_size=2MB --l3_size=32MB '
            '--cacheline_size=64 --cpu-clock=3GHz '
            f'--checkpoint-dir={env.gem5_cpdir(self)} '
            f'--kernel={env.gem5_kernel_path} '
            f'--disk-image={env.hd_raw_path(self.disk_image)} '
            f'--disk-image={env.cfgtar_path(self)} '
            f'--cpu-type={cpu_type} --mem-size={self.mem}MB '
            '--ddio-enabled --ddio-way-part=8 --mem-type=DDR4_2400_16x4 ')

        if env.restore_cp:
            cmd += '-r 0 '

        if len(self.nics) > 0:
            assert len(self.nics) == 1
            nic = self.nics[0]
            cmd += f'--cosim-pci={env.nic_pci_path(nic)} '
            cmd += f'--cosim-shm={env.nic_shm_path(nic)} '
            if cpu_type == 'TimingSimpleCPU':
                cmd += '--cosim-sync '
            if isinstance(nic, I40eNIC):
                cmd += '--cosim-type=i40e '
        return cmd



class CorundumVerilatorNIC(NICSim):
    def resreq_mem(self):
        # this is a guess
        return 512

    def run_cmd(self, env):
        return self.basic_run_cmd(env, 'corundum/corundum_verilator')

class CorundumBMNIC(NICSim):
    def run_cmd(self, env):
        return self.basic_run_cmd(env, 'corundum_bm/corundum_bm')

class I40eNIC(NICSim):
    def run_cmd(self, env):
        return self.basic_run_cmd(env, 'i40e_bm/i40e_bm')



class WireNet(NetSim):
    def run_cmd(self, env):
        assert len(self.nics) == 2
        return '%s/net_wire/net_wire %s %s' % \
                (env.repodir, env.nic_eth_path(self.nics[0]),
                        env.nic_eth_path(self.nics[1]))

class SwitchNet(NetSim):
    def run_cmd(self, env):
        cmd = env.repodir + '/net_switch/net_switch'
        for n in self.nics:
            cmd += ' -s ' + env.nic_eth_path(n)
        return cmd


class NS3DumbbellNet(NetSim):
    def run_cmd(self, env):
        ports = ''
        for n in self.nics:
            if 'server' in n.name:
                ports += '--CosimPortLeft=' + env.nic_eth_path(n) + ' '
            else:
                ports += '--CosimPortRight=' + env.nic_eth_path(n) + ' '

        cmd = env.repodir + '/ns-3' + '/cosim-run.sh cosim cosim-dumbbell-example ' + ports + ' ' + self.opt
        print(cmd)

        return cmd


def create_basic_hosts(e, num, name_prefix, net, nic_class, host_class,
        nc_class, app_class, ip_start=1):
    hosts = []
    for i in range(0, num):
        nic = nic_class()
        #nic.name = '%s.%d' % (name_prefix, i)
        nic.set_network(net)

        host = host_class()
        host.name = '%s.%d' % (name_prefix, i)

        node_config = nc_class()
        node_config.ip = '10.0.0.%d' % (ip_start + i)
        node_config.app = app_class()
        host.set_config(node_config)

        host.add_nic(nic)
        e.add_nic(nic)
        e.add_host(host)

        hosts.append(host)

    return hosts

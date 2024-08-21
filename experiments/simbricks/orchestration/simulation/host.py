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

import simbricks.orchestration.simulation.base as base
import simbricks.orchestration.system as system
import typing as tp
import simbricks.orchestration.experiments as exp
from simbricks.orchestration.experiment.experiment_environment_new import ExpEnv


class HostSim(Simulator):

    def __init__(self, e: exp.Experiment):
        super().__init__(e)
        self.experiment = e
        self.hosts: spec.Host = []
        # need to change type of list to PCI dev
        self.pcidevs: tp.List[spec.NIC] = []

        self.sync_period = 500
        """Period in nanoseconds of sending synchronization messages from this
        device to connected components."""
        self.pci_latency = 500
        self.sync = True
        self.wait = True
    
    def full_name(self) -> str:
        return 'host.' + self.name

    def dependencies(self) -> tp.List[Simulator]:
        deps = []
        for h in self.hosts:
            for dev in h.nics:
                deps.append(dev.sim)
        print(f'host deps: {deps}')
        return deps
    
    def add(self, host: spec.Host):
        self.hosts = host
        self.pcidevs = host.nics
        # host.sim = self
        self.name = f'{self.hosts.id}'
        self.sync_period = host.sync_period
        self.pci_latency = host.pci_channel.latency
        self.sync = host.sync

        self.experiment.add_host(self)

    def config_str(self) -> str:
        return []

    def make_tar(self, path: str) -> None:
        with tarfile.open(path, 'w:') as tar:
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
            for (n, f) in self.hosts.config_files().items():
                f_i = tarfile.TarInfo('guest/' + n)
                f_i.mode = 0o777
                f.seek(0, io.SEEK_END)
                f_i.size = f.tell()
                f.seek(0, io.SEEK_SET)
                tar.addfile(tarinfo=f_i, fileobj=f)
                f.close()    

    def wait_terminate(self) -> bool:
        return self.wait
    

class Gem5Sim(HostSim):

    def __init__(self, e: exp.Experiment):
        super().__init__(e)
        self.experiment = e
        self.name = ''

        self.cpu_type_cp = 'X86KvmCPU'
        self.cpu_type = 'TimingSimpleCPU'
        self.extra_main_args = []
        self.extra_config_args = []
        self.variant = 'fast'
        self.modify_checkpoint_tick = True
        self.wait = True
    
    def full_name(self) -> str:
        return 'host.' + self.name

    def resreq_cores(self) -> int:
        return 1

    def resreq_mem(self) -> int:
        return 4096

    def config_str(self) -> str:
        cp_es = [] if self.nockp else ['m5 checkpoint']
        exit_es = ['m5 exit']
        es = self.hosts.prepare_pre_cp() + self.hosts.app.prepare_pre_cp(self) + cp_es + \
            self.hosts.prepare_post_cp() + self.hosts.app.prepare_post_cp(self) + \
            self.hosts.run_cmds() + self.hosts.cleanup_cmds() + exit_es
        return '\n'.join(es)


    def prep_cmds(self, env: ExpEnv) -> tp.List[str]:
        cmds = [f'mkdir -p {env.gem5_cpdir(self)}']
        if env.restore_cp and self.modify_checkpoint_tick:
            cmds.append(
                f'python3 {env.utilsdir}/modify_gem5_cp_tick.py --tick 0 '
                f'--cpdir {env.gem5_cpdir(self)}'
            )
        return cmds
    

    def run_cmd(self, env: ExpEnv) -> str:
        cpu_type = self.cpu_type
        if env.create_cp:
            cpu_type = self.cpu_type_cp

        cmd = f'{env.gem5_path(self.variant)} --outdir={env.gem5_outdir(self)} '
        cmd += ' '.join(self.extra_main_args)
        cmd += (
            f' {env.gem5_py_path} --caches --l2cache '
            '--l1d_size=32kB --l1i_size=32kB --l2_size=32MB '
            '--l1d_assoc=8 --l1i_assoc=8 --l2_assoc=16 '
            f'--cacheline_size=64 --cpu-clock={self.hosts[0].cpu_freq}'
            f' --sys-clock={self.hosts[0].sys_clock} '
            f'--checkpoint-dir={env.gem5_cpdir(self)} '
            f'--kernel={env.gem5_kernel_path} '
            f'--disk-image={env.hd_raw_path(self.hosts[0].disk_image)} '
            f'--disk-image={env.cfgtar_path(self)} '
            f'--cpu-type={cpu_type} --mem-size={self.hosts[0].memory}MB '
            f'--num-cpus={self.hosts[0].cores} '
            '--mem-type=DDR4_2400_16x4 '
        )


        for dev in self.pcidevs:
            cmd += (
                f'--simbricks-pci=connect:{env.dev_pci_path(dev.sim)}'
                f':latency={self.pci_latency}ns'
                f':sync_interval={self.sync_period}ns'
            )
            if cpu_type == 'TimingSimpleCPU':
                cmd += ':sync'
            cmd += ' '

        return cmd
    

    def wait_terminate(self) -> bool:
        return self.wait
    
class QemuSim(HostSim):

    def __init__(self, e: exp.Experiment):
        super().__init__(e)


    def resreq_cores(self) -> int:
        if self.sync:
            return 1
        else:
            # change it to sum of all hosts
            return self.hosts[0].cores + 1

    def resreq_mem(self) -> int:
        return 8192
    
    def config_str(self) -> str:
        cp_es = ['echo ready to checkpoint']
        exit_es = ['poweroff -f']
        es = self.hosts.prepare_pre_cp() + self.hosts.app.prepare_pre_cp(self) + cp_es + \
            self.hosts.prepare_post_cp() + self.hosts.app.prepare_post_cp(self) + \
            self.hosts.run_cmds() + self.hosts.cleanup_cmds() + exit_es
        return '\n'.join(es)


    def prep_cmds(self, env: ExpEnv) -> tp.List[str]:
        return [
            f'{env.qemu_img_path} create -f qcow2 -o '
            f'backing_file="{env.hd_path(self.hosts[0].disk_image)}" '
            f'{env.hdcopy_path(self)}'
        ]

    def run_cmd(self, env: ExpEnv) -> str:
        accel = ',accel=kvm:tcg' if not self.sync else ''
        if self.hosts[0].kcmd_append:
            kcmd_append = ' ' + self.hosts[0].kcmd_append
        else:
            kcmd_append = ''

        cmd = (
            f'{env.qemu_path} -machine q35{accel} -serial mon:stdio '
            '-cpu Skylake-Server -display none -nic none '
            f'-kernel {env.qemu_kernel_path} '
            f'-drive file={env.hdcopy_path(self)},if=ide,index=0,media=disk '
            f'-drive file={env.cfgtar_path(self)},if=ide,index=1,media=disk,'
            'driver=raw '
            '-append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 '
            f'init=/home/ubuntu/guestinit.sh rw{kcmd_append}" '
            f'-m {self.hosts[0].memory} -smp {self.hosts[0].cores} '
        )

        if self.sync:
            unit = self.hosts[0].cpu_freq[-3:]
            if unit.lower() == 'ghz':
                base = 0
            elif unit.lower() == 'mhz':
                base = 3
            else:
                raise ValueError('cpu frequency specified in unsupported unit')
            num = float(self.hosts[0].cpu_freq[:-3])
            shift = base - int(math.ceil(math.log(num, 2)))

            cmd += f' -icount shift={shift},sleep=off '

        for dev in self.pcidevs:
            cmd += f'-device simbricks-pci,socket={env.dev_pci_path(dev.sim)}'
            if self.sync:
                cmd += ',sync=on'
                cmd += f',pci-latency={self.pci_latency}'
                cmd += f',sync-period={self.sync_period}'
                # if self.sync_drift is not None:
                #     cmd += f',sync-drift={self.sync_drift}'
                # if self.sync_offset is not None:
                #     cmd += f',sync-offset={self.sync_offset}'
            else:
                cmd += ',sync=off'
            cmd += ' '

        return cmd

# Endhost

Code structure:
 - `proto/`: protocol definitions for PCIe and Ethernet channels
 - NIC Simulators:
    + `dummy_nic/`: dummy device illustrating PIO with cosim-pci interface
    + `corundum/`: verilator-based cycle accurate Corundum model
    + `corundum_bm/`: C++ behavioral model for Corundum
    + `i40e_bm/`: Intel XL710 behavioral model
 - Network Simulators:
    + `net_tap/`: Linux tap interface connector for Ethernet channel
    + `net_wire/`: Ethernet wire, connects to Ethernet channels together:w
 - Helper Libraries:
    + `nicsim_common/`: helper library for NIC simulations
    + `netsim_common/`: helper library for network simulations
    + `libnicbm/`: helper library for behavioral nic models

# Building
 - External dependencies for qemu: `libglib2.0-dev libpixman-1-dev`
 - External dependencies for gem5: `scons`, `python-dev`

Then build everything with:
```
make -j`nproc` all external build-images
```

# Running

We use the scripts in the `experiments/` directory. `make` in that directory
should run all the experiments for the paper. This will take a while (>>1h).
While simulations can be run in parallel, some of them use a lot of core, and we
currently don't have jobserver integration, so blindly running make with a high
`-j` parameter here is a bad idea. You can run individual experiment (see
`experiments/*` for their names) with `make out/$NAME/1/ready`, which will
result in log files in `out/$NAME/1/`. Start with one of the qemu simulations.

To run the experiments multiple times which restore from the common check point,
the script should be added to EXP_CP in experiments/makefile. There should be a 
pair script has "-mck" as suffix to that experiment script to make the check point.
(eg. gem5-timing-corundum-verilator-pair-cp.sh AND gem5-timing-corundum-verilator-pair-cp-mck.sh)

The script doesn't need to restore from the common check point, should be added to 
EXP_NCP in experiments/makefile

## Running Qemu

*These instructions apply only if you want to build and run qemu separately and
are not necessary if built with `make external` and run with our experiments
scripts.*

1. Clone from here: `github.com:FreakyPenguin/qemu-cosim.git`
2. Build with `./configure --target-list=x86_64-softmmu --disable-werror --extra-cflags="-I$PATH_TO_THIS_REPO/proto" --enable-cosim-pci`
3. run dummy nic: `rm -rf /tmp/cosim-pci; ./dummy_nic`
4. To run for example (only the last two lines are specific to this project):
```
x86_64-softmmu/qemu-system-x86_64 \
    -machine q35 -cpu host \
    -drive file=/local/endhostsim/vm-image.qcow2,if=virtio \
    -serial mon:stdio -m 2048 -smp 2 -display none -enable-kvm \
    -chardev socket,path=/tmp/cosim-pci,id=cosimcd \
    -device cosim-pci,chardev=cosimcd
```
5. in vm test with:
    * `for read: dd if=/sys/bus/pci/devices/0000\:00\:03.0/resource2 bs=1 skip=64 count=1`
    * `for write: echo a | dd of=/sys/bus/pci/devices/0000\:00\:03.0/resource2 bs=1 seek=64 count=1`

## Running Gem5

*These instructions apply only if you want to build and run gem5 separately and
are not necessary if built with `make external` and run with our experiments
scripts.*

1. Clone from here: `git@github.com:nicklijl/gem5.git`
2. Build with: `scons build/X86/gem5.opt -jX` (with `X` set to # cores)
3. `echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid`
4. run dummy nic: `rm -rf /tmp/cosim-pci; ./dummy_nic`
5. To run for example:
```
./build/X86/gem5.opt \
    configs/cosim/cosim.py \
    --termport=3456 --kernel=$EHSIM/images/vmlinux \
    --disk-image=$EHSIM/images/output-ubuntu1804/ubuntu1804.raw \
    --cpu-type=X86KvmCPU --mem-size=4GB \
    --cosim-pci=/tmp/cosim-pci --cosim-shm=/dev/shm/dummy_nic_shm
```
5. Attach to gem5 terminal: `./util/term/m5term localhost 3456`

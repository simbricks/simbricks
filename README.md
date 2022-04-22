# SimBricks
**End-to-end system simulation through modular combination of component simulators.**

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

# Dependencies

 - Tested to work on Ubuntu 18.04
 - Verilator (branch v4.010)
 - unzip
 - libpcap-dev
 - libglib2.0-dev
 - python (>= 3.7)
 - libgoogle-perftools-dev
 - libboost-iostreams-dev
 - libboost-coroutine-dev
 - scons
 - ninja-build
 - libpixman-1-dev
 - qemu

# Building

First, initialize all submodules:
```
git submodule init
git submodule update
```

Then, build the project, all submodules, and experiment images:
```
make -j`nproc` all external build-images
```

Note: building system images requires KVM support (and KVM permissions).

# Running

A list of available simulations is listed in `experiments/pyexps`.

To run one of the simulations:
```
cd experiments
python3 run.py pyexps/EXP
```
where `EXP` is the name of the simulation file.

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

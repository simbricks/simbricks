1. Clone from here: `github.com:FreakyPenguin/qemu-cosim.git`
2. Build with `./configure --target-list=x86_64-softmmu --disable-werror --extra-cflags="-I$PATH_TO_THIS_REPO/proto" --enable-cosim-pci`
3. To run for example (only the last line is specific to this project):
```
x86_64-softmmu/qemu-system-x86_64 \
    -machine q35 -cpu host \
    -drive file=/local/endhostsim/vm-image.qcow2,if=virtio \
    -serial mon:stdio -m 2048 -smp 2 -display none -enable-kvm \
    -chardev socket,path=/tmp/cosim-pci,id=cosimcd \
    -device cosim-pci,chardev=cosimcd
```

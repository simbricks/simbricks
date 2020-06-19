#!/bin/bash

if [ ! -f local-config.sh ] ; then
    echo "local-config.sh does not exist"
    exit 1
fi

source local-config.sh

if [ ! -d "$EHSIM_BASE" ] ; then
    echo "\$EHSIM_BASE should be set to the absolute path of the root"\
        "of this repo (local-config.sh)"
    exit 1
fi
if [ ! -f "$QEMU_CMD" ] ; then
    echo "\$QEMU_CMD should be set to the absolute path to a QEMU instance"\
        "with cosim support (local-config.sh)"
    exit 1
fi
if [ ! -d "$GEM5_BASE" ] ; then
    echo "\$GEM5_BASE should be set to the absolute path to a built gem5 repo"\
        "(local-config.sh)"
    exit 1
fi
if [ ! -d "$NS3_BASE" ] ; then
    echo "\$NS3_BASE should be set to the absolute path to a built ns3 repo"\
        "(local-config.sh)"
    exit 1
fi

QEMU_IMAGE=$EHSIM_BASE/images/output-ubuntu1804/ubuntu1804
QEMU_KERNEL=$EHSIM_BASE/images/bzImage
GEM5_IMAGE=$EHSIM_BASE/images/output-ubuntu1804/ubuntu1804.raw
GEM5_KERNEL=$EHSIM_BASE/images/vmlinux

# Args:
#   - experiment name
init_out() {
  export OUTDIR=./out/$1
  rm -rf $OUTDIR
  mkdir -p $OUTDIR
}

# Args:
#   - Instance name
#   - Cosim instance
#   - secondary hard drive
run_qemu() {
    img_a="$OUTDIR/qemu.hd.a.$1"
    img_b="$OUTDIR/qemu.hd.b.$1"
    pcisock="$OUTDIR/pci.$2"
    rm -f $img_a $img_b
    echo Creating disk for qemu $1
    qemu-img create -f qcow2 -o backing_file=$QEMU_IMAGE $img_a
    cp $3 $img_b
    echo Starting qemu $1
    $QEMU_CMD -machine q35 -cpu host \
        -drive file=$img_a,if=ide,index=0 \
        -drive file=$img_b,if=ide,index=1,driver=raw \
        -kernel $QEMU_KERNEL \
        -append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 init=/home/ubuntu/guestinit.sh rw" \
        -serial mon:stdio -m $((4 * 1024)) -smp 1 -display none -enable-kvm \
        -nic none \
        -chardev socket,path=$pcisock,id=cosimcd \
        -device cosim-pci,chardev=cosimcd &>$OUTDIR/qemu.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - Cosim instance
#   - secondary hard drive
#   - cpu type
#   - checkpoint dir
#   - extra flags
run_gem5() {
    echo Starting gem5 $1
    pcisock="$OUTDIR/pci.$2"
    shm="$OUTDIR/shm.$2"
    cpdir="$OUTDIR/checkpoints.$5"
    mkdir -p $cpdir
    $GEM5_BASE/build/X86/gem5.opt \
        --outdir=$OUTDIR/gem5.out.$1 \
        $GEM5_BASE/configs/cosim/cosim.py \
        --kernel=$GEM5_KERNEL --disk-image=$GEM5_IMAGE --disk-image=$3 \
        --cpu-type=$4 --mem-size=4GB --cosim-pci=$pcisock --cosim-shm=$shm \
        --checkpoint-dir="$cpdir" $6 \
        &>$OUTDIR/gem5.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
run_corundum_verilator() {
    echo Starting corundum_verilator $1
    $EHSIM_BASE/corundum/corundum_verilator \
        $OUTDIR/pci.$1 $OUTDIR/eth.$1 $OUTDIR/shm.$1 \
            &>$OUTDIR/corundum_verilator.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
run_corundum_bm() {
    echo Starting corundum_bm $1
    $EHSIM_BASE/corundum_bm/corundum_bm \
        $OUTDIR/pci.$1 $OUTDIR/eth.$1 $OUTDIR/shm.$1 \
        &>$OUTDIR/corundum_bm.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - sim instance 1
#   - sim instance 2
run_wire() {
    echo Starting wire $1
    $EHSIM_BASE/net_wire/net_wire \
        $OUTDIR/eth.$2 $OUTDIR/eth.$3 &>$OUTDIR/wire.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - Port names
run_ns3_bridge() {
    ports=""
    for p in $2; do
        epath="`readlink -f $OUTDIR/eth.$p`"
        ports="$ports --CosimPort=$epath"
    done
    $NS3_BASE/cosim-run.sh cosim-bridge-example \
        $ports &>$OUTDIR/ns3_bridge.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - Left Port names
#   - Right Port names
#   - Other args
run_ns3_dumbbell() {
    ports=""
    for p in $2; do
        epath="`readlink -f $OUTDIR/eth.$p`"
        ports="$ports --CosimPortLeft=$epath"
    done
    for p in $3; do
        epath="`readlink -f $OUTDIR/eth.$p`"
        ports="$ports --CosimPortRight=$epath"
    done

    $NS3_BASE/cosim-run.sh cosim-dumbbell-example \
        $ports $4 &>$OUTDIR/ns3_bridge.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

cleanup() {
    echo Cleaning up
    for p in $ALL_PIDS ; do
        kill $p &>/dev/null
    done
    sleep 1
    for p in $ALL_PIDS ; do
        kill -KILL $p &>/dev/null
    done

    rm -f $OUTDIR/{qemu.hd.*,shm.*,pci.*,eth.*}
}

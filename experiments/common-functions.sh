#!/bin/bash

EHSIM_BASE="$(readlink -f $(dirname ${BASH_SOURCE[0]})/..)"
QEMU_CMD="$EHSIM_BASE/qemu/x86_64-softmmu/qemu-system-x86_64"
QEMU_IMG="$EHSIM_BASE/qemu/qemu-img"
GEM5_BASE="$EHSIM_BASE/gem5"
NS3_BASE="$EHSIM_BASE/ns-3"
OUTDIR_BASE="$EHSIM_BASE/experiments/out"
WORKDIR_BASE="$OUTDIR_BASE"

if [ -f local-config.sh ] ; then
    source local-config.sh
fi


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

QEMU_IMAGE=$EHSIM_BASE/images/output-base/base
QEMU_KERNEL=$EHSIM_BASE/images/bzImage
GEM5_IMAGE=$EHSIM_BASE/images/output-base/base.raw
GEM5_KERNEL=$EHSIM_BASE/images/vmlinux

# Args:
#   - experiment name
init_out() {
  export OUTDIR=$OUTDIR_BASE/$1/$2
  export WORKDIR=$WORKDIR_BASE/$1/$2
  rm -rf $OUTDIR $WORKDIR
  mkdir -p $OUTDIR $WORKDIR
  date > $OUTDIR/starttime
}

# Args:
#   - Instance name
#   - Cosim instance
#   - secondary hard drive
#   - [optional primary image name: default ubuntu1804-base]
#   - [optional: additinoal qemu arguments]
run_qemu() {
    img_a="$WORKDIR/qemu.hd.a.$1"
    img_b="$WORKDIR/qemu.hd.b.$1"
    pcisock="$WORKDIR/pci.$2"
    rm -f $img_a $img_b
    echo Creating disk for qemu $1
    if [ -z "$4" ]; then
        $QEMU_IMG create -f qcow2 -o backing_file=$QEMU_IMAGE $img_a
    else
        $QEMU_IMG create -f qcow2 -o backing_file="$EHSIM_BASE/images/output-$4/$4" $img_a
    fi
    cp $3 $img_b
    echo Starting qemu $1
    #i40e.debug=0x8fffffff
    #hugepages=1024
    $QEMU_CMD -machine q35 -cpu host \
        -drive file=$img_a,if=ide,index=0,media=disk \
        -drive file=$img_b,if=ide,index=1,media=disk,driver=raw \
        -kernel $QEMU_KERNEL \
        -append "earlyprintk=ttyS0 console=ttyS0 root=/dev/sda1 init=/home/ubuntu/guestinit.sh rw" \
        -serial mon:stdio -m $((16 * 1024)) -smp 1 -display none -enable-kvm \
        -nic none \
        -chardev socket,path=$pcisock,id=cosimcd \
        -device cosim-pci,chardev=cosimcd \
        $5 &>$OUTDIR/qemu.$1.log &
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
#   - [optional primary image name: default ubuntu1804-base]
run_gem5() {
    echo Starting gem5 $1
    pcisock="$WORKDIR/pci.$2"
    shm="$WORKDIR/shm.$2"
    cpdir="$WORKDIR/../checkpoint/checkpoints.$5"
    mkdir -p $cpdir

    if [ -z "$7" ]; then
        img="$GEM5_IMAGE"
    else
        img="$EHSIM_BASE/images/output-$7/$7.raw"
    fi

    $GEM5_BASE/build/X86/gem5.opt \
        --outdir=$OUTDIR/gem5.out.$1 \
        $GEM5_BASE/configs/cosim/cosim.py \
        --caches --l2cache --l3cache\
        --l1d_size=32kB \
        --l1i_size=32kB \
        --l2_size=2MB \
        --l3_size=32MB \
        --cacheline_size=64 \
        --cpu-clock=3GHz \
        --kernel=$GEM5_KERNEL --disk-image=$img --disk-image=$3 \
        --cpu-type=$4 --mem-size=16GB --cosim-pci=$pcisock --cosim-shm=$shm \
        --ddio-enabled --ddio-way-part=8 --mem-type=DDR4_2400_16x4 \
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
        $WORKDIR/pci.$1 $WORKDIR/eth.$1 $WORKDIR/shm.$1 \
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
        $WORKDIR/pci.$1 $WORKDIR/eth.$1 $WORKDIR/shm.$1 \
        &>$OUTDIR/corundum_bm.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
run_i40e_bm() {
    echo Starting i40e $1
    $EHSIM_BASE/i40e_bm/i40e_bm \
        $WORKDIR/pci.$1 $WORKDIR/eth.$1 $WORKDIR/shm.$1 \
        &>$OUTDIR/i40e_bm.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - sim instance 1
#   - sim instance 2
#   - [optional: pcap filename]
run_wire() {
    echo Starting wire $1
    if [ -z "$4" ]; then
        pcap=
    else
        pcap="$OUTDIR/$4.pcap"
    fi

    $EHSIM_BASE/net_wire/net_wire \
        $WORKDIR/eth.$2 $WORKDIR/eth.$3 $pcap &>$OUTDIR/wire.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - sim instance 1
#   - sim instance 2
#   - [sim instance 3, ...]
run_switch() {
    echo Starting switch $1

    args=
    for iface in ${@:2}
    do
        args="$args -s $WORKDIR/eth.$iface"
    done

    $EHSIM_BASE/net_switch/net_switch \
        $args &>$OUTDIR/switch.$1.log &
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
        epath="`readlink -f $WORKDIR/eth.$p`"
        ports="$ports --CosimPort=$epath"
    done
    $NS3_BASE/cosim-run.sh cosim cosim-bridge-example \
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
        epath="`readlink -f $WORKDIR/eth.$p`"
        ports="$ports --CosimPortLeft=$epath"
    done
    for p in $3; do
        epath="`readlink -f $WORKDIR/eth.$p`"
        ports="$ports --CosimPortRight=$epath"
    done

    $NS3_BASE/cosim-run.sh cosim cosim-dumbbell-example \
        $ports $4 &>$OUTDIR/ns3_dumbbell.$1.log &
    pid=$!
    ALL_PIDS="$ALL_PIDS $pid"
    return $pid
}

# Args:
#   - Instance name
#   - Client Port names
#   - Server Port names
#   - Other args
run_ns3_sequencer() {
    ports=""
    for p in $2; do
        epath="`readlink -f $WORKDIR/eth.$p`"
        ports="$ports --ClientPort=$epath"
    done
    for p in $3; do
        epath="`readlink -f $WORKDIR/eth.$p`"
        ports="$ports --ServerPort=$epath"
    done

    $NS3_BASE/cosim-run.sh sequencer sequencer-single-switch-example \
        $ports $4 &>$OUTDIR/ns3_sequencer.$1.log &
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

    if [ "$OUTDIR" != "$WORKDIR" ]; then
        rm -rf $WORKDIR
    else
        rm -f $WORKDIR/{qemu.hd.*,shm.*,pci.*,eth.*}
    fi
    date >>$OUTDIR/endtime
}

sighandler() {
    echo "Caught Interrupt, aborting...."
    cleanup
    exit 1
}

trap "sighandler" SIGINT

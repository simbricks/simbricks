###################################
Quick Start
###################################

******************************
Building
******************************

Requirements:

  * TAS is built on top of Intel DPDK for direct access to the NIC. We have
    tested this version with dpdk versions 17.11.9, 18.11.5, 19.11.

Assuming that dpdk is installed in ``~/dpdk-inst`` TAS can be built as follows
(for a system installation of dpdk the ``RTE_SDK`` variable does not need to be
passed explicitly):

.. code-block:: bash

   make RTE_SDK=~/dpdk-inst


This will build the TAS service (binary ``tas/tas``), client libraries (in
``lib/``), and a few debugging tools (in ``tools/``).


******************************
Running
******************************

Before running TAS the following steps are necessary:

   * Make sure ``hugetlbfs`` is mounted on ``/dev/hugepages`` and enough huge
     pages are allocated for TAS and dpdk.

   * Binding the NIC to the dpdk driver, as with any other dpdk application (for
     Intel NICs use ``vfio`` because ``uio`` does not support multiple
     interrupts).

.. code-block:: bash

   sudo modprobe vfio-pci
   sudo mount -t hugetlbfs nodev /dev/hugepages
   echo 1024 | sudo tee /sys/devices/system/node/node*/hugepages/hugepages-2048kB/nr_hugepages
   sudo ~/dpdk-inst/sbin/dpdk-devbind  -b vfio-pci 0000:08:00.0

To run (``--ip-addr`` and ``--fp-cores-max`` are the minimum arguments typically
needed to run tas):

.. code-block:: bash

   sudo code/tas/tas --ip-addr=10.0.0.1/24 --fp-cores-max=2

Once tas is running, applications that directly link to ``libtas`` or
``libtas_sockets`` can be run directly. To run an unmodified application with
sockets interposition run as follows (for example):

.. code-block:: bash

   sudo LD_PRELOAD=lib/libtas_interpose.so ../benchmarks/micro_rpc/echoserver_linux 1234 1 foo 8192 1


******************************
In Qemu/KVM
******************************

For functional testing and development TAS can run in Qemu (with or without
acceleration through KVM). We have tested this with the ``virtio`` dpdk driver.
By default, the qemu virtio device only provides a single queue, and thus only
allows TAS to run on a single core. To run a virtual machine with support for
multiple queue, qemu requires a tap device with multi-queue support enabled.

Here is an example sequence of commands to create a tap device with multi queue
support and then start a qemu instance that binds this tap device to a
multi-queue virtio device:

.. code-block:: bash

   sudo ip link add tastap0 type tuntap
   sudo ip tuntap add mode tap multi_queue name tastap0
   sudo ip link set dev tastap0 up
   qemu-system-x86_64 \
       -machine q35 -cpu host \
       -drive file=vm1.qcow2,if=virtio \
       -netdev tap,ifname=tastap0,script=no,downscript=no,vhost=on,queues=8,id=nInt\
       -device virtio-net-pci,mac=52:54:00:12:34:56,vectors=18,mq=on,netdev=nInt \
       -serial mon:stdio -m 8192 -smp 16 -display none -enable-kvm


Inside the virtual machine, the following sequence of commands first takes the
linux network interface down, binds it to the ``uio_pci_generic`` driver that
the dpdk virtio PMD supports, and then reserves huge pages:

.. code-block:: bash

   sudo ifconfig enp0s2 down
   sudo modprobe uio
   sudo modprobe uio_pci_generic
   sudo dpdk-devbind.py -b uio_pci_generic 0000:00:02.0
   echo 1024 | sudo tee /sys/devices/system/node/node*/hugepages/hugepages-2048kB/nr_hugepages

Virtio does not support all the NIC features that we depend on in physical NICs.
In particular virtio does not support transmit checksum offload or the RSS
redirection table TAS uses for scaling up and down. The dpdk virtio PMD also
does not support multiple MSI-X interrupts.  To run TAS given these constraints,
the following command line parameters disable the use of these features (note
that this implies busy polling and no autoscaling):

.. code-block:: bash

   sudo code/tas/tas --ip-addr=10.0.0.1/24 --fp-cores-max=8 \
       --fp-no-xsumoffload --fp-no-ints --fp-no-autoscale


******************************
Kernel NIC Interface
******************************

TAS supports the DPDK kernel NIC interface (KNI) to pass packets to the Linux
kernel network stack. With KNI enabled, TAS becomes an opt-in fastpath where
TAS-enabled applications operate through TAS, and other applications can use the
Linux network stack as before, sharing the same physical NIC.

To run TAS with KNI the first step is to load the ``rte_kni`` kernel module.
Next, when run with the ``--kni-name=`` option, TAS will create a KNI dummy
network interface with the specified name. After assigning an IP address to this
network interface, the Linux network stack can send and receive packets through
this interface as long as TAS is running. Here is the complete sequence of
commands:

.. code-block:: bash

   sudo modprobe rte_kni
   sudo code/tas/tas --ip-addr=10.0.0.1/24 --kni-name=tas0
   # in separate terminal
   sudo ifconfig tas0 10.0.0.1/24 up

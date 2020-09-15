#!/bin/bash
insmod mqnic.ko
ip link set dev eth0 up
ip addr add 10.1.0.100/24 dev eth0
/root/nopaxos/sequencer/sequencer -c /root/sequencer.config
poweroff

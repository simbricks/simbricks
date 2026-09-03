#!/bin/bash -eux
#
# Runs last: remove build deps, sanitize identity/logs, fstrim so the raw
# conversion stays sparse.

set -eux
export DEBIAN_FRONTEND=noninteractive

# Leftover dhcp leases
rm -f /var/lib/dhcp3/* /var/lib/dhcp/*
rm -rf /tmp/*

# apt caches / build deps
apt-get -y autoremove --purge
apt-get -y clean
apt-get -y autoclean
rm -rf /var/lib/apt/lists/*

# Shell history
unset HISTFILE
rm -f /root/.bash_history /home/ubuntu/.bash_history

# Logs
find /var/log -type f -exec truncate -s 0 {} +
: >/var/log/lastlog
: >/var/log/wtmp
: >/var/log/btmp

# Reset machine identity so cloned VMs regenerate it
truncate -s 0 /etc/machine-id || true

# Trim unused blocks -> small sparse raw after qemu-img convert -S
fstrim -av || true

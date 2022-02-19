#!/bin/bash -eux

# Cleaning up leftover dhcp leases
rm -f /var/lib/dhcp3/* /var/lib/dhcp/*

rm -rf /tmp/*

# Cleanup apt cache
apt-get -y autoremove --purge
apt-get -y clean
apt-get -y autoclean

unset HISTFILE
rm -f /root/.bash_history
rm -f /home/ubuntu/.bash_history

# Clean up log files
find /var/log -type f | while read f; do echo -ne '' > "${f}"; done;

# Clearing last login information
>/var/log/lastlog
>/var/log/wtmp
>/var/log/btmp

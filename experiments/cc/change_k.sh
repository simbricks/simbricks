#!/bin/bash
if [ -z $1 ]; then
    echo "no arg given"
    exit -1
fi

# This file executes the BCM command to change the K value for a profile 0.
# Before doing this, one need to assign a profile 0 to a relevant ports.
# copy this file to the machine with switch is connected via serial.
# See the below link for other commands to setup the DCTCP ECN makring.
# https://docs.google.com/presentation/d/1nyJOYap6yiSoxHBIDarSBjxGFVGJtEqSv01oVoJYuoc

K=$1

#This is where it creates a BCM script for minicom to send.
cat <<EOF > bcmscript.txt
send modify mmu_wred_drop_curve_profile_0 0 1 max_drop_rate=0xe max_thd=$K min_thd=$K
EOF

#Execute minicom and send the command above, then send exit command via pipe.
#exit command is stored in a separate file due to use of special characters.
cat exit_minicom.txt | sudo minicom -S bcmscript.txt -C capture.txt -t vt100

#Output will be captured and displayed. No output is expected in a succesful execution.
cat capture.txt

echo "Setting threshold to $K"

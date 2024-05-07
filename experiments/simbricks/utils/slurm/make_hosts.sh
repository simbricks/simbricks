
nodes="`scontrol show hostnames $SLURM_JOB_NODELIST`"
leader="`echo $nodes | awk '{print $1}'`"
workers="`echo $nodes | awk '{for (i=2; i<=NF; i++) print $i}'`"

# Build hosts.json
echo "["
ip="`getent hosts $leader | awk '{print \$1}'`"
echo "{\"type\": \"local\", \"ip\": \"$ip\"}"

for w in $workers
do
	ip="`getent hosts $w | awk '{print \$1}'`"
	echo ",{\"type\": \"remote\", \"workdir\": \"/simbricks\", \"host\": \"$ip\", \"ip\": \"$ip\", \"ssh_args\": [\"-p2222\"], \"scp_args\": [\"-P2222\"]}"
done
echo "]"

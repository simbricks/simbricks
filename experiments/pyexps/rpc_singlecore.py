import modes.experiments as exp
import modes.simulators as sim
import modes.nodeconfig as node


msg_sizes = [64, 1024, 8092]
stacks = ['mtcp', 'tas', 'linux']
num_clients = 1

experiments = []
for msg_size in msg_sizes:
  for stack in stacks:
    e = exp.Experiment('qemu-ib-switch-rpc-%s-1t-1fpc-%db-0mpc' % (stack,msg_size))
    net = sim.SwitchNet()
    e.add_network(net)

    if stack == 'tas':
        n = node.TASNode
    elif stack == 'mtcp':
        n = node.MtcpNode
    else:
        n = node.I40eLinuxNode

    servers = sim.create_basic_hosts(e, 1, 'server', net, sim.I40eNIC, sim.QemuHost,
            n, node.RPCServer)

    clients = sim.create_basic_hosts(e, num_clients, 'client', net, sim.I40eNIC,
            sim.QemuHost, n, node.RPCClient, ip_start = 2)

    for h in servers + clients:
        h.node_config.cores = 1 if stack != 'tas' else 3
        h.node_config.fp_cores = 1
        h.node_config.app.threads = 1
        h.node_config.app.max_bytes = msg_size

        if stack == 'linux':
            h.node_config.disk_image = 'tas'

    servers[0].sleep = 5

    for c in clients:
        c.wait = True
        c.node_config.app.server_ip = servers[0].node_config.ip

    experiments.append(e)


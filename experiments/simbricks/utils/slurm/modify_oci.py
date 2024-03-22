# Copyright 2023 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""Script to modify an OCI container JSON file."""

import argparse
import json
import os
import os.path
import shlex

parser = argparse.ArgumentParser()
parser.add_argument('--json', help='Path to the container json file')
parser.add_argument('--cmd', help='Command to run')
parser.add_argument(
    '--mount',
    type=str,
    nargs='+',
    default=[],
    metavar='H:G',
    help='mount directory into guest'
)
args = parser.parse_args()

with open(args.json, 'r', encoding='utf-8') as f:
    c = json.loads(f.read())

c['process']['terminal'] = False
c['process']['args'] = shlex.split(args.cmd)
c['process']['cwd'] = '/simbricks/experiments'

for k in c['process']['capabilities']:
    c['process']['capabilities'][k].append('CAP_SYS_CHROOT')
    c['process']['capabilities'][k].append('CAP_SETUID')
    c['process']['capabilities'][k].append('CAP_SETGID')

c['process']['rlimits'][0]['hard'] = 8192
c['process']['rlimits'][0]['soft'] = 8192

c['root']['path'] = os.path.dirname(os.path.abspath(args.json)) + '/rootfs'
c['root']['readonly'] = False

id_mapping = {
    'containerID': 1,
    'hostID': (os.getuid() + 1 - 1000) * 100000,
    'size': 100000
}
c['linux']['uidMappings'] = [
    # mapping for root uid
    {
        'containerID': 0, 'hostID': os.getuid(), 'size': 1
    },
    id_mapping  # add mappings for other uids
]
c['linux']['gidMappings'] = [
    # mapping for root gid
    {
        'containerID': 0, 'hostID': os.getgid(), 'size': 1
    },
    id_mapping,  # add mappings for other gids
    # kvm group
    {
        'containerID': 100001, 'hostID': 105, 'size': 1
    }
]

#del c['linux']['resources']

c['linux']['devices'] = [{
    'path': '/dev/kvm', 'type': 'c', 'major': 10, 'minor': 232
}]

for i in range(0, len(c['linux']['namespaces'])):
    if c['linux']['namespaces'][i]['type'] == 'network':
        del c['linux']['namespaces'][i]
        break

for m in args.mount:
    ps = m.split(':')
    c['mounts'].append({
        'source': ps[0],
        'destination': ps[1],
        'type': 'none',
        'options': ['rbind', 'nosuid', 'noexec', 'nodev', 'rw']
    })

with open(args.json, 'w', encoding='utf-8') as f:
    f.write(json.dumps(c))

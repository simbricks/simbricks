# Copyright 2021 Max Planck Institute for Software Systems, and
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

import json
import re
import sys


def transform_internal(ts, component, msg):
    if not component.startswith('system.pc.simbricks_0'):
        return None
    elif component.endswith('.pio'):
        return None
    elif msg.startswith('read device register ') and 'res=' in msg:
        return None
    elif (
        msg.startswith('our dma') or msg.startswith('issuing dma') or
        msg.startswith('processing ip packet') or
        msg.startswith('transmitting non-ip packet') or
        msg.startswith('transmitting ip packet')
    ):
        return None

    return f'{ts} {msg}'


def transform_external(ts, msg):
    if msg.startswith('igbe: requesting restart clock:') or \
       msg == 'igbe: scheduled' or \
       msg == 'igbe: rescheduling next cycle' or \
       msg == 'igbe: no next cycle scheduled':
        return None
    elif msg.startswith('[rxdesc]') or msg.startswith('[txdesc]'):
        msg = msg[9:]

    return f'{ts} {msg}'


if len(sys.argv) != 3:
    print('Usage: pci_validation.py JSON-DIR VARIANT')
    print('       VARIANT can be internal or external')
    sys.exit(1)

outdir = sys.argv[1]
variant = sys.argv[2]

with open(
    f'{outdir}/pci_validation-{variant}-1.json', 'r', encoding='utf-8'
) as f:
    data = json.load(f)

if variant == 'internal':
    line_pat = re.compile(r'(\d*):\s*([a-zA-Z0-9\._]*):\s*(.*)')
    it = iter(data['sims']['host.client']['stdout'])
    transform = transform_internal
else:
    line_pat = re.compile(r'(\d*):\s*([a-zA-Z0-9\._]*):\s*(.*)')
    it = iter(data['sims']['nic.client.']['stderr'])
    transform = transform_external

# we're doing the comparision for the client
for l in it:
    m = line_pat.match(l)
    if not m:
        continue

    l = transform(m.group(1), m.group(3).lower())
    if l:
        print(l)

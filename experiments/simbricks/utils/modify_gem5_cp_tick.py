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
"""Script to modify the tick of a gem5 checkpoint."""

import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--cpdir', help='Path to gem5 checkpoint directory', required=True
    )
    parser.add_argument(
        '--tick',
        help='The new value for the checkpoint\'s tick',
        type=int,
        required=True
    )

    args = parser.parse_args()

    # Modify tick of all checkpoints in gem5 checkpoint directory to new_tick
    for cp in filter(
        lambda file: file.startswith('cpt.'), os.listdir(args.cpdir)
    ):
        cp_file = f'{args.cpdir}/{cp}/m5.cpt'
        if not os.path.exists(cp_file):
            print(
                f'WARN {os.path.basename(__file__)}: checkpoint '
                f'{args.cpdir}/{cp} doesn\'t have a m5.cpt'
            )
            continue
        with open(cp_file, 'r', encoding='utf-8') as f:
            data: str = f.read()
        curtick = int(cp.split('.')[1])
        newdata = data.replace(f'curTick={curtick}', f'curTick={args.tick}', 1)
        with open(cp_file, 'w', encoding='utf-8') as f:
            f.write(newdata)
        print(
            f'INFO {os.path.basename(__file__)}: successfully set tick of '
            f'{args.cpdir}/{cp} to {args.tick}'
        )


if __name__ == '__main__':
    main()

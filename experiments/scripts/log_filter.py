#!/usr/bin/env python3
"""Follow a simulator log and write the lines matching a pattern to a summary file.

Example of a script run as a fragment process next to a simulator, see
gem5_streams_demo.py. Only the standard library is used because it runs with
whatever Python the executor has. The log may not exist yet at start and may be
truncated while it is followed; on SIGINT/SIGTERM the rest of the log is read
before exiting, so the summary is complete once the process is gone. --ready is
created once the signal handlers are in place.
"""

import argparse
import pathlib
import re
import signal
import sys
import time


class LogFilter:
    def __init__(self, log, pattern, out):
        self.log = log
        self.pattern = pattern
        self.out = out
        self.offset = 0
        self.partial = ""
        self.stop = False

    def request_stop(self, *_):
        self.stop = True

    def drain(self, out):
        try:
            size = self.log.stat().st_size
        except FileNotFoundError:
            return
        if size < self.offset:  # truncated or replaced
            self.offset = 0
            self.partial = ""
        if size == self.offset:
            return
        with open(self.log, "r", encoding="utf-8", errors="replace") as log:
            log.seek(self.offset)
            data = log.read()
            self.offset = log.tell()
        lines = (self.partial + data).split("\n")
        self.partial = lines.pop()
        for line in lines:
            if self.pattern.search(line):
                out.write(line + "\n")
        out.flush()

    def run(self, interval):
        self.out.parent.mkdir(parents=True, exist_ok=True)
        with open(self.out, "w", encoding="utf-8") as out:
            while not self.stop:
                self.drain(out)
                time.sleep(interval)
            self.drain(out)
            if self.partial and self.pattern.search(self.partial):
                out.write(self.partial + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", required=True, help="file to follow")
    parser.add_argument("--pattern", required=True, help="regular expression to keep lines by")
    parser.add_argument("--out", required=True, help="summary file to write")
    parser.add_argument("--ready", help="file to create once signals are handled")
    parser.add_argument("--interval", type=float, default=0.2, help="poll interval in seconds")
    args = parser.parse_args()

    filt = LogFilter(pathlib.Path(args.log), re.compile(args.pattern), pathlib.Path(args.out))
    signal.signal(signal.SIGINT, filt.request_stop)
    signal.signal(signal.SIGTERM, filt.request_stop)
    if args.ready:
        pathlib.Path(args.ready).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.ready).touch()
    filt.run(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())

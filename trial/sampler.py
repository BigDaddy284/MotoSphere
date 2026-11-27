"""TRIAL ONLY (FND-054): write down, once a second, how many TCP connections the machine has.

Usage: sampler.py <file to write to>
Standard library only. Stops when the file "<file>.stop" appears.
"""

import collections
import datetime
import pathlib
import subprocess
import sys
import time

out = pathlib.Path(sys.argv[1])
stop = pathlib.Path(sys.argv[1] + ".stop")
with out.open("a", encoding="utf-8") as log:
    while not stop.exists():
        began = time.monotonic()
        answer = subprocess.run(["netstat", "-an"], capture_output=True, text=True, check=False)
        states: collections.Counter[str] = collections.Counter()
        ports: set[str] = set()
        to_4173 = 0
        for line in answer.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "TCP":
                states[parts[3]] += 1
                port = parts[1].rsplit(":", 1)[-1]
                if port.isdigit() and int(port) >= 1025 and parts[3] != "LISTENING":
                    ports.add(parts[1])
                if parts[2].endswith(":4173"):
                    to_4173 += 1
        now = datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S")
        took = time.monotonic() - began
        said = " ".join(f"{state}={count}" for state, count in sorted(states.items()))
        log.write(f"{now} all={sum(states.values())} local={len(ports)} to4173={to_4173} took={took:.2f}s {said}\n")
        log.flush()
        time.sleep(max(0.0, 1.0 - took))

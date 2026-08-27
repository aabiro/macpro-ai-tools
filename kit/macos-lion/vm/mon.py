#!/usr/bin/env python3
"""Send commands to the QEMU monitor over its unix socket."""
import socket, sys, time
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/tmp/lion-monitor")
time.sleep(0.5)
try: s.recv(65536)
except Exception: pass
for cmd in sys.argv[1:]:
    s.sendall((cmd + "\n").encode())
    time.sleep(0.8)
time.sleep(1.5)
try: print(s.recv(65536).decode(errors="replace")[-400:])
except Exception: pass
s.close()

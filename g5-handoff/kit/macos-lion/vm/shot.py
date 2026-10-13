import socket, time, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/tmp/lion-monitor")
time.sleep(0.6); s.recv(65536)
s.sendall(b"screendump /home/macpro/oc/vm.ppm\n")
time.sleep(3.0)
try: print(s.recv(65536).decode(errors="replace")[:300])
except Exception: pass
s.close()

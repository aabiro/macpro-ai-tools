#!/usr/bin/env python3
"""Check that what the handoff documents claim is actually true of this machine.

The docs are the deliverable. A wrong port, a command that does not exist, or a
path that moved is worse than no documentation, because the reader trusts it and
then concludes the machine is broken.
"""
import os, re, shutil, subprocess, sys

DOCDIR = "/usr/local/share/doc/macpro/kit"

def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""

text = ""
for f in sorted(os.listdir(DOCDIR)):
    if f.endswith(".md"):
        text += open(os.path.join(DOCDIR, f), errors="replace").read() + "\n"

print("=== 1. file paths the docs reference ===")
paths = set()
for m in re.finditer(r"(/etc|/opt|/usr/local|/var/lib|/var/log|/srv|/home/macpro|/mnt|/boot)[A-Za-z0-9._/+-]{2,70}", text):
    p = m.group(0).rstrip(".,);:`")
    if any(c in p for c in "<>*$") or p.endswith("/"):
        continue
    paths.add(p)
missing = sorted(p for p in paths if not os.path.exists(p))
for p in missing:
    print("   MISSING: %s" % p)
print("   -> %d missing of %d referenced" % (len(missing), len(paths)))

print()
print("=== 2. commands in backticks that are not installed ===")
SKIP = set("""root macpro yes no text keep lax active enabled ok none null true false
dynamic share main stop start serve setup check fix chat undo help list status test
set show add install update restore create latest min max nomodeset single ro rw
force noauto nofail sse2 sendreceive share shadow gshadow env on off up down
suggest explain login auth reload restart enable disable""".split())
cmds = set()
for m in re.finditer(r"`([a-z][a-z0-9_.-]{1,24})`", text):
    c = m.group(1)
    if c in SKIP or "." in c:
        continue
    cmds.add(c)
absent = sorted(c for c in cmds if not shutil.which(c))
for c in absent:
    print("   not installed: %s" % c)
print("   -> %d of %d backticked tokens are not commands (some are prose)" % (len(absent), len(cmds)))

print()
print("=== 3. services and ports the docs claim ===")
listening = sh(["ss", "-lntup"])
for svc, port in [("ai-gateway","8081"), ("cockpit-web","3000"), ("vscode-web","8443"),
                  ("cockpit","9090"), ("smbd","445"), ("syncthing","8384")]:
    st = sh(["systemctl","is-active",svc]).strip() or "n/a"
    up = "yes" if (":"+port) in listening else "NO"
    print("   %-12s port %-5s service=%-10s listening=%s" % (svc, port, st, up))

print()
print("=== 4. versions the docs state, against reality ===")
CLAIMS = {
    "claude":   ("1.0.128",  ["claude","--version"]),
    "gemini":   ("0.55.1",   ["gemini","--version"]),
    "node":     ("24.19.0",  ["node","--version"]),
    "npm":      ("11.17.0",  ["npm","--version"]),
    "uv":       ("0.12.5",   ["uv","--version"]),
    "podman":   ("5.4.2",    ["podman","--version"]),
    "docker":   ("26.1.5",   ["docker","--version"]),
    "ffmpeg":   ("7.1.5",    ["ffmpeg","-version"]),
    "openshot-qt": ("3.1.1", ["openshot-qt","--version"]),
    "timeshift":("24.06.6",  ["timeshift","--version"]),
    "flatpak":  ("1.16.6",   ["flatpak","--version"]),
}
for name,(claimed, cmd) in sorted(CLAIMS.items()):
    if not shutil.which(cmd[0]):
        print("   %-13s NOT INSTALLED (doc claims %s)" % (name, claimed))
        continue
    out = sh(cmd)
    print("   %-13s doc=%-10s actual=%s" % (name, claimed,
          "MATCH" if claimed in out else "DIFFERS -> " + (out.strip().splitlines() or [""])[0][:60]))

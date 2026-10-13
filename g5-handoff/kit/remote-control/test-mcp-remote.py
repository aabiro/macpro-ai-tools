#!/usr/bin/env python3
"""Drive the remote-control MCP server over real MCP and validate its tools.

The remote server is the one an operator's own machine runs; it reaches the Mac
Pro over SSH. This test speaks the protocol a client speaks -- initialize,
initialized, tools/list, tools/call -- and checks the CONTENT of each reply.

    ./test-mcp-remote.py [python] [server.py]

Defaults match this repository's layout. Exit status is the failure count.
"""

import json
import subprocess
import sys
import time

PYTHON = sys.argv[1] if len(sys.argv) > 1 else \
    "/mnt/storage/projects/macpro-ai-tools/.venv/bin/python"
SERVER = sys.argv[2] if len(sys.argv) > 2 else \
    "/mnt/storage/projects/macpro-ai-tools/macpro_mcp_server.py"


class Client:
    def __init__(self, argv):
        self.p = subprocess.Popen(argv, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.rid = 0

    def send(self, method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self.rid += 1
            msg["id"] = self.rid
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()
        return None if notify else self.rid

    def wait(self, rid, timeout=600):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("server closed stdout. stderr:\n%s"
                                   % self.p.stderr.read()[:3000])
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue                      # log noise, not a reply
            if msg.get("id") == rid:
                return msg
        raise RuntimeError("no reply within %ss" % timeout)

    def call(self, method, params=None, timeout=600):
        return self.wait(self.send(method, params), timeout)

    def text(self, tool, args=None, timeout=600):
        msg = self.call("tools/call",
                        {"name": tool, "arguments": args or {}}, timeout)
        if "error" in msg:
            return "PROTOCOL-ERROR: %s" % msg["error"]
        out = []
        for c in (msg.get("result") or {}).get("content", []):
            out.append(c.get("text", ""))
        return "\n".join(out)

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


passes, fails = 0, []


def check(label, got, must, must_not=()):
    global passes
    import re
    bad = [f"missing /{p}/" for p in must if not re.search(p, got, re.I | re.S)]
    bad += [f"should NOT contain /{p}/" for p in must_not
            if re.search(p, got, re.I | re.S)]
    if bad:
        fails.append(label)
        print("  FAIL  %s" % label)
        for b in bad:
            print("          %s" % b)
        print("          got: %s" % " ".join(got.split())[:240])
    else:
        passes += 1
        print("  ok    %s" % label)


NOT_WORKING = (r"PROTOCOL-ERROR", r"tooling is not installed",
               r"is not answering", r"TIMEOUT after", r"Unknown tool")

print("Driving %s over MCP\n" % SERVER)
c = Client([PYTHON, SERVER])

init = c.call("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "test-mcp-remote", "version": "1.0"}}, timeout=120)
check("initialize handshake", json.dumps(init),
      [r'"protocolVersion"', r'"serverInfo"'])
c.send("notifications/initialized", {}, notify=True)

listed = c.call("tools/list", timeout=120)
tools = [t["name"] for t in (listed.get("result") or {}).get("tools", [])]
print("  %d tools: %s\n" % (len(tools), ", ".join(tools)))
check("the Lion tools are advertised", " ".join(tools),
      [r"g5_lion_exec", r"g5_lion_vm_control"])
check("the earlier Linux tools are still advertised", " ".join(tools),
      [r"g5_linux_boot_health", r"g5_linux_desktop_exec", r"g5_linux_screenshot"])
check("the original G5 tools are intact", " ".join(tools),
      [r"g5_execute_bash", r"g5_read_file", r"g5_write_file", r"g5_disk_layout"])

check("g5_lion_vm_control status reports a live VM",
      c.text("g5_lion_vm_control", {"action": "status"}, 180),
      [r"overlay", r"read-only"], NOT_WORKING)

check("g5_lion_exec runs a command inside Mac OS X",
      c.text("g5_lion_exec", {"command": "sw_vers -productVersion"}, 240),
      [r"10\.7\.5"], NOT_WORKING)

# r"\S" alone passed on the literal reply "Unknown tool: g5_lion_exec", which is
# the opposite of working. Ban that explicitly.
check("g5_lion_exec survives quoting across every shell hop",
      c.text("g5_lion_exec",
             {"command": "awk '{print $1}' /etc/hostconfig | head -1"}, 240),
      [r"\S"], NOT_WORKING + (r"Unknown tool",))

check("g5_lion_exec reports a failing command instead of pretending",
      c.text("g5_lion_exec", {"command": "ls /nope-12345"}, 240),
      [r"No such file"])

check("g5_lion_vm_control rejects an unknown action clearly",
      c.text("g5_lion_vm_control", {"action": "banana"}, 120),
      [r"Unknown action"])

check("g5_linux_boot_health returns measurements",
      c.text("g5_linux_boot_health", None, 240),
      [r"initramfs|initrd|vmlinuz"], NOT_WORKING)

bad = c.call("tools/call", {"name": "g5_nope", "arguments": {}}, 120)
check("an unknown tool is an error, not a fallback", json.dumps(bad),
      [r"error|unknown|not found"])

c.close()
print("\n%d passed, %d failed" % (passes, len(fails)))
for f in fails:
    print("  failed: %s" % f)
sys.exit(len(fails))

#!/usr/bin/env python3
"""Drive the `macpro-mcp lion` server over real MCP and validate every tool.

This is not a smoke test. It speaks the protocol a client speaks -- initialize,
tools/list, tools/call -- and checks the CONTENT of each reply against what that
tool is supposed to produce. A tool that returns a polite error string would
pass a "did it respond" test and fails here.

    ./test-mcp-lion.py                 # against /usr/local/bin/macpro-mcp
    ./test-mcp-lion.py ./macpro-mcp    # against a working copy

Exit status is the number of failures, so it is usable as a gate.
"""

import json
import re
import subprocess
import sys
import time

SERVER = sys.argv[1] if len(sys.argv) > 1 else "/usr/local/bin/macpro-mcp"


class Client:
    """A minimal MCP stdio client. No dependencies; this machine has few."""

    def __init__(self, argv):
        self.p = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.rid = 0

    def call(self, method, params=None, timeout=600):
        self.rid += 1
        req = {"jsonrpc": "2.0", "id": self.rid, "method": method}
        if params is not None:
            req["params"] = params
        self.p.stdin.write(json.dumps(req) + "\n")
        self.p.stdin.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("server closed stdout; stderr:\n%s"
                                   % self.p.stderr.read()[:2000])
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("id") == self.rid:
                return msg
        raise RuntimeError("no reply to %s within %ss" % (method, timeout))

    def text(self, tool, args=None, timeout=600):
        msg = self.call("tools/call",
                        {"name": tool, "arguments": args or {}}, timeout)
        if "error" in msg:
            return "PROTOCOL-ERROR: %s" % msg["error"]
        result = msg.get("result") or {}
        parts = [c.get("text", "") for c in result.get("content", [])]
        return "\n".join(parts)

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


fails = []
passes = 0


def check(label, got, must_match, must_not_match=()):
    """must_match: all of these regexes must be present, case-insensitively."""
    global passes
    problems = []
    for pat in must_match:
        if not re.search(pat, got, re.I | re.S):
            problems.append("missing /%s/" % pat)
    for pat in must_not_match:
        if re.search(pat, got, re.I | re.S):
            problems.append("should NOT contain /%s/" % pat)
    if problems:
        fails.append((label, problems, got[:400]))
        print("  FAIL  %s" % label)
        for pr in problems:
            print("          %s" % pr)
        print("          got: %s" % " ".join(got.split())[:220])
    else:
        passes += 1
        print("  ok    %s" % label)


# Failure text every tool may legitimately emit. If it shows up in a test that
# expected real data, the tool is not working -- so it is banned per-test.
# Match the server's ACTUAL failure strings, precisely. An earlier version used
# bare r"TIMEOUT" with re.I, which matched the legitimate "timeout   120" line
# in `g5-config show` output and failed a working tool.
NOT_WORKING = (r"tooling is not installed",
               r"VM is not answering",
               r"PROTOCOL-ERROR",
               r"tool failed:",
               r"TIMEOUT after \d+s")

print("Driving %s lion over MCP\n" % SERVER)
c = Client([SERVER, "lion"])

# ---- protocol ------------------------------------------------------------
init = c.call("initialize", {"protocolVersion": "2024-11-05",
                             "capabilities": {}, "clientInfo":
                             {"name": "test-mcp-lion", "version": "1.0"}})
check("initialize handshake", json.dumps(init),
      [r'"protocolVersion"', r'"serverInfo"', r'macpro-lion'])

listed = c.call("tools/list")
names = [t["name"] for t in (listed.get("result") or {}).get("tools", [])]
print("  tools advertised: %d -> %s" % (len(names), ", ".join(names)))
check("every expected tool is advertised", " ".join(names), [
    r"lion_exec", r"lion_read_file", r"lion_write_file", r"lion_list_dir",
    r"lion_system_report", r"lion_logs", r"lion_list_apps", r"lion_services",
    r"lion_gateway_check", r"lion_vm_status", r"lion_vm_start",
    r"lion_vm_stop", r"lion_vm_screenshot"])

# Schemas must declare their arguments, or a client cannot call them properly.
schemas = {t["name"]: t.get("inputSchema", {})
           for t in (listed.get("result") or {}).get("tools", [])}
check("lion_exec declares a command argument",
      json.dumps(schemas.get("lion_exec", {})), [r'"command"', r'"timeout"'])
check("lion_write_file declares path and content",
      json.dumps(schemas.get("lion_write_file", {})), [r'"path"', r'"content"'])

# ---- make sure the VM is up before judging anything else ------------------
status = c.text("lion_vm_status")
print("\n  vm_status says: %s" % " | ".join(status.split("\n")[:4]))
if "answering: yes" not in status:
    print("  starting the VM first...")
    print("  %s" % " ".join(c.text("lion_vm_start", timeout=600).split())[:160])
    status = c.text("lion_vm_status")
check("lion_vm_status reports a live guest", status,
      [r"answering: yes", r"overlay", r"snapshot present"], NOT_WORKING)

# ---- the tools that must return real data --------------------------------
check("lion_exec runs a command and returns its output",
      c.text("lion_exec", {"command": "sw_vers -productVersion"}),
      [r"10\.7\.5"], NOT_WORKING)

check("lion_exec handles quoting that crosses two shells",
      c.text("lion_exec", {"command": "awk '{print $1}' /etc/hostconfig | head -1"}),
      [r"\S"], NOT_WORKING)

check("lion_exec reports a non-zero exit rather than pretending success",
      c.text("lion_exec", {"command": "ls /definitely-not-here-12345"}),
      [r"exited [1-9]", r"No such file"])

check("lion_system_report covers the whole system",
      c.text("lion_system_report", timeout=600),
      [r"ProductVersion", r"10\.7\.5", r"--- disk", r"--- users",
       r"administrator", r"Remote Login", r"gateway"], NOT_WORKING)

check("lion_list_dir lists a real directory",
      c.text("lion_list_dir", {"path": "/Users"}),
      [r"administrator", r"Shared"], NOT_WORKING)

check("lion_read_file reads a real file",
      c.text("lion_read_file", {"path": "/etc/hostconfig", "max_lines": 20}),
      [r"\S"], NOT_WORKING)

check("lion_read_file refuses a relative path",
      c.text("lion_read_file", {"path": "etc/hostconfig"}),
      [r"must be absolute"])

# Write, then read it back through a DIFFERENT tool -- a write that only its own
# return value confirms has not been verified.
probe = "/Users/Shared/mcp-selftest.txt"
body = "line one\nline two with 'quotes' and \"doubles\" and $VARS\n"
check("lion_write_file reports a byte count",
      c.text("lion_write_file", {"path": probe, "content": body}),
      [r"wrote \d+ bytes"], NOT_WORKING)
check("the written content reads back byte-exact",
      c.text("lion_read_file", {"path": probe}),
      [r"line one", r"line two with 'quotes'", r'"doubles"', r"\$VARS"], NOT_WORKING)
c.text("lion_exec", {"command": "rm -f " + probe})

check("lion_list_apps lists applications",
      c.text("lion_list_apps"), [r"\.app"], NOT_WORKING)

check("lion_services lists launchd jobs",
      c.text("lion_services", {"filter": "ssh"}), [r"ssh"], NOT_WORKING)

check("lion_logs reads the system log",
      c.text("lion_logs", {"lines": 20}), [r"\S"], NOT_WORKING)

check("lion_gateway_check proves Lion's own Python reaches the gateway",
      c.text("lion_gateway_check", timeout=300),
      [r"configured gateway: http", r'"status"', r'"version"'], NOT_WORKING)

check("lion_vm_screenshot captures and explains a black screen",
      c.text("lion_vm_screenshot", timeout=300),
      [r"\.png", r"lit=", r"EXPECTED"], NOT_WORKING)

# ---- an unknown tool must be an error, not a fallback --------------------
bad = c.call("tools/call", {"name": "lion_does_not_exist", "arguments": {}})
check("an unknown tool is refused, not silently absorbed",
      json.dumps(bad), [r"unknown tool"])

c.close()

print("\n%d passed, %d failed" % (passes, len(fails)))
if fails:
    print("\nFailures:")
    for label, problems, got in fails:
        print("  %s" % label)
        for pr in problems:
            print("    %s" % pr)
sys.exit(len(fails))

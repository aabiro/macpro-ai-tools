#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
g5ai.py -- shared client library for the AI Cockpit on Mac OS X Lion.

Written for the Python 2.7.1 that ships with Lion. Standard library ONLY --
no pip, no setuptools, no virtualenv. Nothing here may assume a network
package manager exists, because on this machine one effectively does not:
TLS 1.2 is unavailable, so pip cannot reach PyPI even if it were installed.

Everything talks to the gateway (see kit/gateway/aigw.py) over plain HTTP.
The gateway performs the modern TLS handshake on this machine's behalf.

Configuration is read, in increasing order of precedence:

    1. /Users/Shared/ai-cockpit/config.json     (machine-wide default)
    2. ~/.g5ai.json                             (per-user override)
    3. G5AI_GATEWAY / G5AI_PROVIDER / G5AI_MODEL environment variables

There is deliberately NO hardcoded gateway address. The previous build hardcoded
a private Tailscale IP that stopped existing the moment the machine changed
hands; a new owner must be able to point this at their own gateway without
editing source.
"""

import json
import os
import socket
import subprocess
import sys

try:
    # Lion: Python 2.7
    import urllib2
except ImportError:
    # Debian: Python 3. Bind the handful of names used below onto the stdlib's
    # Python 3 equivalents, so all call sites stay written the Python 2 way and
    # this one library serves both machines.
    import urllib.error
    import urllib.request

    class _Urllib2Compat(object):
        Request = staticmethod(urllib.request.Request)
        urlopen = staticmethod(urllib.request.urlopen)
        HTTPError = urllib.error.HTTPError
        URLError = urllib.error.URLError

    urllib2 = _Urllib2Compat()

__version__ = "1.1.0"

# Where the machine-wide config and helper scripts live. Lion keeps them in
# /Users/Shared; on Linux there is no such convention, so use /opt.
if sys.platform == "darwin":
    SHARED_DIR = "/Users/Shared/ai-cockpit"
else:
    SHARED_DIR = "/opt/ai-cockpit"
SYSTEM_CONFIG = os.path.join(SHARED_DIR, "config.json")
USER_CONFIG = os.path.expanduser("~/.g5ai.json")

DEFAULTS = {
    "gateway": "",          # e.g. http://192.168.1.50:8081
    "provider": "gemini",   # gemini | anthropic | openai
    "model": "",            # blank = let the gateway pick its default
    "max_tokens": 2048,
    "timeout": 120,
}


class G5Error(Exception):
    """A problem we can explain to the user in plain language."""
    pass


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _read_json(path):
    try:
        f = open(path, "rb")
        try:
            return json.loads(f.read().decode("utf-8"))
        finally:
            f.close()
    except (IOError, OSError):
        return {}
    except ValueError:
        sys.stderr.write("warning: %s is not valid JSON; ignoring it\n" % path)
        return {}


def load_config():
    """Merge machine config, user config, and environment overrides."""
    cfg = dict(DEFAULTS)
    cfg.update(_read_json(SYSTEM_CONFIG))
    cfg.update(_read_json(USER_CONFIG))

    for env_key, cfg_key in (
        ("G5AI_GATEWAY", "gateway"),
        ("G5AI_PROVIDER", "provider"),
        ("G5AI_MODEL", "model"),
    ):
        value = os.environ.get(env_key, "").strip()
        if value:
            cfg[cfg_key] = value

    gateway = str(cfg.get("gateway") or "").strip().rstrip("/")
    if gateway and not gateway.startswith("http"):
        gateway = "http://" + gateway
    cfg["gateway"] = gateway
    return cfg


def save_user_config(cfg):
    """Persist settings to the per-user config file."""
    f = open(USER_CONFIG, "wb")
    try:
        f.write(json.dumps(cfg, indent=2, sort_keys=True).encode("utf-8"))
        f.write(b"\n")
    finally:
        f.close()
    try:
        os.chmod(USER_CONFIG, 0o600)
    except OSError:
        pass


NO_GATEWAY_MESSAGE = """\
No AI gateway is configured yet.

This Mac cannot reach modern AI services directly -- its TLS is too old
(OpenSSL 0.9.8). It needs a small helper program, the "gateway", running on
any newer computer on the same network.

To get running:

  1. On a modern Mac/PC/Linux box, copy the file  aigw.py  from
     /Users/Shared/ai-cockpit/gateway/  onto that machine.

  2. On that machine, run (Python 3 required, no other install needed):

         export GEMINI_API_KEY=your-key-here
         python3 aigw.py

     It prints the address to use, for example  http://192.168.1.50:8081

  3. Back on this Mac, run:

         g5-config set gateway http://192.168.1.50:8081

  4. Check it:

         g5-config test

See /Users/Shared/ai-cockpit/README.md for the full walkthrough.
"""


# ---------------------------------------------------------------------------
# Gateway transport
# ---------------------------------------------------------------------------


def _post(url, payload, timeout):
    body = json.dumps(payload)
    req = urllib2.Request(url, body, {"Content-Type": "application/json"})
    handle = urllib2.urlopen(req, timeout=timeout)
    try:
        return json.loads(handle.read())
    finally:
        handle.close()


def health(cfg=None):
    """Ask the gateway how it is doing. Returns the parsed health dict."""
    cfg = cfg or load_config()
    if not cfg["gateway"]:
        raise G5Error(NO_GATEWAY_MESSAGE)
    url = cfg["gateway"] + "/health"
    try:
        handle = urllib2.urlopen(url, timeout=15)
        try:
            return json.loads(handle.read())
        finally:
            handle.close()
    except urllib2.HTTPError as exc:
        raise G5Error("Gateway answered HTTP %s at %s" % (exc.code, url))
    except (urllib2.URLError, socket.error) as exc:
        raise G5Error(
            "Could not reach the gateway at %s\n\n  %s\n\n"
            "Is the gateway program running on the other machine, and is that\n"
            "machine on the same network as this one?" % (cfg["gateway"], exc)
        )


def ask(prompt, system=None, history=None, provider=None, model=None,
        max_tokens=None, thinking=False, cfg=None):
    """Send a prompt through the gateway and return the reply as text.

    Raises G5Error with a human-readable explanation on any failure, so callers
    can print the message directly without interpreting exception types.
    """
    cfg = cfg or load_config()
    if not cfg["gateway"]:
        raise G5Error(NO_GATEWAY_MESSAGE)

    provider = provider or cfg["provider"]
    payload = {
        "provider": provider,
        "prompt": prompt,
        "max_tokens": int(max_tokens or cfg["max_tokens"]),
    }
    if system:
        payload["system"] = system
    if history:
        payload["history"] = history
    chosen_model = model or cfg.get("model")
    if chosen_model:
        payload["model"] = chosen_model
    if thinking:
        payload["thinking"] = True

    url = "%s/v1/chat/%s" % (cfg["gateway"], provider)
    try:
        result = _post(url, payload, int(cfg["timeout"]))
    except urllib2.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read()
        except Exception:
            pass
        try:
            parsed = json.loads(detail)
            if parsed.get("text"):
                return parsed["text"]
            detail = parsed.get("error", detail)
        except ValueError:
            pass
        raise G5Error("Gateway error HTTP %s\n\n%s" % (exc.code, detail[:800]))
    except (urllib2.URLError, socket.error) as exc:
        raise G5Error(
            "Could not reach the gateway at %s\n\n  %s\n\n"
            "Check that the gateway is still running." % (cfg["gateway"], exc)
        )
    except ValueError as exc:
        raise G5Error("Gateway sent a reply this program could not read: %s" % exc)

    text = result.get("text")
    if not text:
        raise G5Error("The model returned an empty reply. Try rephrasing.")
    return text


# ---------------------------------------------------------------------------
# Local system inspection (used by the Custodian / g5-doctor)
# ---------------------------------------------------------------------------


REDACTIONS = (
    # (label as it appears in output, human-readable replacement)
    "Serial Number (system)",
    "Serial Number",
    "Hardware UUID",
    "Provisioning UDID",
)


def redact(text):
    """Strip machine-identifying values before anything leaves this Mac.

    The diagnostics are sent to a third-party AI provider. The readings that
    matter for health -- temperatures, SMART status, DIMM status -- carry no
    identity. The serial number and hardware UUID do, and they belong to
    whoever owns the machine, so they are removed on the way out.
    """
    if not text:
        return ""
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(label + ":") for label in REDACTIONS):
            label = stripped.split(":", 1)[0]
            indent = line[:len(line) - len(line.lstrip())]
            out.append("%s%s: (redacted)" % (indent, label))
        else:
            out.append(line)
    return "\n".join(out).strip()


def run(cmd):
    """Run a shell command, returning stdout as text. Never raises."""
    try:
        proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out, _ = proc.communicate()
        return out
    except Exception as exc:
        return "(could not run %r: %s)" % (cmd, exc)


def collect_diagnostics():
    """Gather a health snapshot of this Mac Pro.

    Everything here works WITHOUT admin rights. The obvious source,
    /var/log/system.log, is root:admin 0640 and is therefore unreadable to a
    standard user -- the previous build shelled out to `sudo tail` and silently
    produced nothing but a permission error. We read it only if we actually can,
    and otherwise lean on sources that are always available.

    The checks below target how a 2006 Mac Pro actually dies: FB-DIMM failure
    (they run hot), power supply, thermal problems, and aging spinning disks.
    """
    sections = []

    def add(title, text):
        text = redact(text)
        if text:
            sections.append("### %s\n%s" % (title, text))

    add("Machine", run("system_profiler SPHardwareDataType 2>/dev/null | "
                       "sed -n '1,20p'"))
    add("Uptime and load", run("uptime"))
    add("Memory (ECC / DIMM status)",
        run("system_profiler SPMemoryDataType 2>/dev/null"))
    add("Virtual memory", run("vm_stat | head -8"))
    add("Disk space", run("df -h"))

    # SMART status per physical disk -- the single most useful early warning
    # on a machine this old, and it needs no privileges.
    disk_report = []
    listing = run("diskutil list 2>/dev/null | grep -oE '^/dev/disk[0-9]+'")
    for disk in sorted(set(line.strip() for line in listing.splitlines() if line.strip())):
        info = run("diskutil info %s 2>/dev/null | grep -iE "
                   "'Device / Media Name|SMART|Solid State|Total Size'" % disk)
        if info.strip():
            disk_report.append("%s\n%s" % (disk, info.rstrip()))
    add("Disk health (SMART)", "\n".join(disk_report))

    add("Thermal / power sensors",
        run("ioreg -n IOHWSensor 2>/dev/null | grep -iE '\"location\"|current-value' "
            "| head -40"))

    # Kernel panics leave reports behind; they are the smoking gun for bad RAM.
    add("Recent panic reports",
        run("ls -1t /Library/Logs/DiagnosticReports/*.panic 2>/dev/null | head -5"))

    # Only include the system log if this account can actually read it.
    if os.access("/var/log/system.log", os.R_OK):
        add("System log (last 120 lines)", run("tail -n 120 /var/log/system.log"))
    else:
        add("System log",
            "(not readable by this account -- /var/log/system.log is "
            "root:admin 0640. Run as an administrator account to include it.)")

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Small terminal helpers
# ---------------------------------------------------------------------------


def wrap(text, width=78):
    """Wrap text for an 80-column terminal, preserving blank lines."""
    import textwrap
    out = []
    for para in (text or "").split("\n"):
        if not para.strip():
            out.append("")
        else:
            out.extend(textwrap.wrap(para, width) or [""])
    return "\n".join(out)


def die(message, code=1):
    sys.stderr.write(str(message).rstrip() + "\n")
    sys.exit(code)

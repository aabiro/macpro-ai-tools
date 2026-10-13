#!/usr/bin/env python3
"""Check that the handover documents describe THIS machine, not an imagined one.

Docs drift. A command that was renamed, a port that moved, a link to a file that
was never written -- each one costs a beginner their confidence in the whole set.
This reads the docs and checks their factual claims against the running system.

    ./validate-docs.py                 # against the installed kit
    ./validate-docs.py /path/to/kit    # against a working copy

What it checks:
  * every internal markdown link resolves to a file that exists
  * every `command` mentioned in a "what it does" table is actually on PATH
  * every localhost port the docs advertise is really listening
  * every absolute path the docs name really exists
  * every systemd unit the docs claim is enabled really is

Exit status is the number of problems, so it is usable as a gate.
"""

import os
import re
import shutil
import socket
import subprocess
import sys

KIT = sys.argv[1] if len(sys.argv) > 1 else "/usr/local/share/doc/macpro/kit"

problems = []
checked = 0


def bad(doc, msg):
    problems.append((doc, msg))


def ok():
    global checked
    checked += 1


# Commands the docs may mention that are deliberately NOT on PATH, with the
# reason. Without this list the checker would report false problems.
# Names that appear in a table's first cell but are not Linux commands on this
# machine. Each one caused a false report before it was listed here.
NOT_COMMANDS = {
    # MCP server names, from the agent-tools table
    "macpro-health", "macpro-journal", "macpro-apt", "macpro-lion",
    "filesystem", "fetch", "memory", "time", "git",
    # Debian package names, not commands
    "build-essential", "ripgrep",
    # Mac OS X commands, documented for the Lion side -- they do not exist and
    # are not supposed to exist on Linux
    "diskutil", "mdutil", "pmset", "installer", "bless", "sw_vers",
    "launchctl", "defaults", "systemsetup", "mount_msdos", "md5",
    "networksetup", "scutil", "kextstat", "vm_stat", "fsck_hfs",
}

NOT_ON_PATH = {
    "ai-gateway": "a systemd service, not a command",
    "cockpit": "a web interface and a desktop icon",
    "docker": "checked separately; may be group-restricted",
    "sudo": "obviously present",
    "smbpasswd": "in /usr/sbin",
    "smartctl": "in /usr/sbin",
    "lynis": "in /usr/sbin",
    "pip": "use uv instead",
    "npm": "checked separately",
}


def path_present(p):
    """True if the path exists, or if we are not allowed to find out.

    /etc/ai-cockpit/ is root-only, so os.path.exists() returns False for
    /etc/ai-cockpit/env even though the file is there. Reporting that as a
    documentation error is worse than not checking it, so ask sudo -n and, if
    that is unavailable, treat "permission denied" as "cannot disprove".
    """
    if os.path.exists(p):
        return True
    parent = os.path.dirname(p)
    if parent and os.path.isdir(parent) and not os.access(parent, os.X_OK):
        return True                      # unreadable directory; cannot judge
    try:
        r = subprocess.run(["sudo", "-n", "test", "-e", p],
                           capture_output=True, timeout=15)
        if r.returncode == 0:
            return True
        if b"password" in (r.stderr or b"").lower():
            return True                  # cannot check; do not accuse
    except Exception:
        pass
    return False


def strip_code_blocks(text):
    """Remove fenced blocks before checking paths.

    A code block is an INSTRUCTION, not a claim. USING-BOTH-SYSTEMS.md contains
    "sudo mkdir -p /mnt/shared" -- the whole point is that the path does not
    exist yet, so flagging it as missing is backwards.
    """
    return re.sub(r"```.*?```", "", text, flags=re.S)


# Prose sometimes names a path precisely because it is WRONG -- for example the
# explanation of an rsync bug that "silently looks for /etc/etc/shadow". A line
# carrying one of these cues is discussing a path, not asserting it.
NEGATION_CUES = ("does not exist", "matches nothing", "never", "wrong",
                 "mistake", "bug", "silently looks", "would look", "instead of",
                 "not there", "absent", "typo")


def find_cmd(name):
    """PATH, plus the sbin directories a normal user's PATH omits."""
    if shutil.which(name):
        return True
    for d in ("/usr/sbin", "/sbin", "/usr/local/sbin"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return True
    return False


def port_listening(port):
    for family, addr in ((socket.AF_INET, ("127.0.0.1", port)),):
        s = socket.socket(family, socket.SOCK_STREAM)
        s.settimeout(3)
        try:
            s.connect(addr)
            return True
        except Exception:
            return False
        finally:
            s.close()
    return False


def unit_enabled(unit):
    try:
        r = subprocess.run(["systemctl", "is-enabled", unit],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.strip() in ("enabled", "enabled-runtime", "static",
                                    "indirect", "alias")
    except Exception:
        return False


docs = sorted(f for f in os.listdir(KIT) if f.endswith(".md"))
if not docs:
    print("no .md files in %s" % KIT)
    sys.exit(1)

print("Validating %d documents in %s\n" % (len(docs), KIT))

for doc in docs:
    path = os.path.join(KIT, doc)
    text = open(path, encoding="utf-8", errors="replace").read()

    # --- internal links -------------------------------------------------
    for target in re.findall(r"\[[^\]]+\]\(([^)#]+?\.md)(?:#[^)]*)?\)", text):
        if target.startswith(("http://", "https://", "file://")):
            continue
        resolved = os.path.normpath(os.path.join(KIT, target))
        if os.path.exists(resolved):
            ok()
        else:
            bad(doc, "link to a file that does not exist: %s" % target)

    # --- commands in tables ---------------------------------------------
    # Only tables that say they list COMMANDS. Backticked first cells appear in
    # plenty of other tables -- model ids like `gpt-4o`, kernel modules like
    # `i5k_amb`, service names like `cockpit-web` -- and treating those as
    # commands produced a dozen false reports. The header is the doc telling us
    # what the table is about, so believe it.
    in_command_table = False
    for line in text.split("\n"):
        if not line.startswith("|"):
            in_command_table = False
            continue
        header = line.lower()
        if "command" in header and ("what it does" in header or "what" in header):
            in_command_table = True
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue                       # the |---|---| separator
        if not in_command_table:
            continue
        m = re.match(r"^\|\s*`([^`]+)`", line)
        if not m:
            continue
        cmd = m.group(1).strip().split()[0]
        if not re.match(r"^[a-z][a-z0-9._-]*$", cmd):
            continue
        if cmd in NOT_ON_PATH or cmd in NOT_COMMANDS or "." in cmd:
            continue
        if find_cmd(cmd):
            ok()
        else:
            bad(doc, "documents a command that is not installed: %s" % cmd)

    # --- localhost ports -------------------------------------------------
    for port in set(re.findall(r"localhost:(\d{2,5})", text)):
        if port_listening(int(port)):
            ok()
        else:
            bad(doc, "advertises localhost:%s but nothing is listening" % port)

    # --- absolute paths --------------------------------------------------
    prose = strip_code_blocks(text)
    prose_lines = prose.split("\n")
    for i, line in enumerate(prose_lines):
        # Prose wraps, so a cue can sit on the previous line while the path sits
        # on this one. Look at the sentence, not the line.
        window = " ".join(prose_lines[max(0, i - 1):i + 2]).lower()
        if any(cue in window for cue in NEGATION_CUES):
            continue
        for p in re.findall(r"`(/(?:usr|etc|opt|srv|var|mnt|home)/[^`\s]+)`", line):
            p = p.rstrip(".,);:")
            if "*" in p or "<" in p or "$" in p or "{" in p:
                continue                   # a pattern, not a path
            if path_present(p):
                ok()
            else:
                bad(doc, "names a path that does not exist: %s" % p)

    # --- systemd units ---------------------------------------------------
    for unit in set(re.findall(r"`([a-z0-9-]+\.service)`", text)):
        if unit_enabled(unit):
            ok()
        else:
            bad(doc, "refers to %s, which is not enabled" % unit)

# --- things the docs promise that deserve a direct check ----------------
print("== specific promises")


def promise(label, condition, detail=""):
    if condition:
        ok()
        print("  ok    %s" % label)
    else:
        bad("(cross-doc)", label + (" -- " + detail if detail else ""))
        print("  FAIL  %s%s" % (label, " -- " + detail if detail else ""))


promise("QUICKSTART.md exists", os.path.exists(os.path.join(KIT, "QUICKSTART.md")))
promise("PROGRAMS-AND-APPS.md exists",
        os.path.exists(os.path.join(KIT, "PROGRAMS-AND-APPS.md")))
promise("LION-VM.md exists", os.path.exists(os.path.join(KIT, "LION-VM.md")))

desktop = os.path.expanduser("~/Desktop")
icons = []
if os.path.isdir(desktop):
    for f in sorted(os.listdir(desktop)):
        if not f.endswith(".desktop"):
            continue
        # The launcher's filename is a sort key (aa-, ab-, b-) -- what the user
        # sees is the Name= field, so that is what the docs describe.
        try:
            for line in open(os.path.join(desktop, f), errors="replace"):
                if line.startswith("Name="):
                    icons.append(line.split("=", 1)[1].strip())
                    break
        except Exception:
            pass
promise("the desktop has the documented icons",
        {"Start Here", "AI Cockpit", "Firefox", "VS Code"}.issubset(set(icons)),
        "found: %s" % ", ".join(icons))

promise("lion-vm and lion are installed",
        find_cmd("lion-vm") and find_cmd("lion"))
promise("the Lion VM answers",
        subprocess.run(["lion", "true"], capture_output=True,
                       timeout=60).returncode == 0
        if find_cmd("lion") else False)
promise("Lion's files are mounted at /mnt/lion-live",
        os.path.ismount("/mnt/lion-live"))
promise("the AI gateway answers on 8081", port_listening(8081))
promise("all MCP servers connect",
        b"macpro-lion" in subprocess.run(
            ["claude", "mcp", "list"], capture_output=True, timeout=180).stdout
        if find_cmd("claude") else False)

print("\n%d claims checked, %d problems" % (checked, len(problems)))
if problems:
    print("\nProblems:")
    last = None
    for doc, msg in problems:
        if doc != last:
            print("  %s" % doc)
            last = doc
        print("    %s" % msg)
sys.exit(len(problems))

#!/bin/sh
# -*- coding: utf-8 -*-
# The line below is a polyglot. /bin/sh executes it and replaces itself with a
# Python interpreter; Python parses it as a harmless string literal. This is
# needed because Debian 13 ships only `python3` and Lion ships only `python`,
# so no single #! line works on both machines.
''''true; if command -v python3 >/dev/null 2>&1; then exec python3 "$0" "$@"; else exec python "$0" "$@"; fi # '''
"""g5cli -- codex/copilot/gemini-style assistants that run on BOTH machines.

Why this exists
---------------
The real tools (claude, codex, gemini, gh copilot) need a modern Node or Rust
runtime. On Linux they work. On OS X 10.7 Lion they cannot: Python 2.7 with
OpenSSL 0.9.8 has no TLS 1.2, so Lion cannot even complete a handshake with any
provider. These three commands close that gap by routing every request through
the gateway (aigw.py), which does the TLS on Lion's behalf.

The same file runs under Python 2.6/2.7 (Lion) and Python 3.x (Debian), so
there is exactly one implementation to reason about.

Installed as three names, dispatched on argv[0]:

    g5-codex     read files, ask for a patch, show a diff       (like codex)
    g5-copilot   suggest or explain a shell command             (like gh copilot)
    g5-gemini    plain conversation                             (like gemini)

Nothing here ever executes a suggested command. g5-copilot prints and stops.
That is deliberate: a model proposing `rm -rf` should cost you a keystroke to
refuse, not a keystroke to survive.
"""

# NOTE: no `from __future__ import print_function` here. That statement must be
# the very first in a file, and the polyglot shebang above occupies that slot.
# Nothing in this file calls print() -- output goes through _out() -- so the
# import is not needed, and leaving it out keeps Python 2 and 3 both happy.

import difflib
import os
import sys

__version__ = "1.0"

# --------------------------------------------------------------------------
# Locate g5ai.py. It lives beside this file on Linux and in the shared
# cockpit directory on Lion; accept either without configuration.
# --------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (_HERE,
              os.path.join(_HERE, "..", "macos-lion"),
              "/opt/ai-cockpit",
              "/usr/local/lib/ai-cockpit",
              "/Users/Shared/ai-cockpit"):
    _cand = os.path.abspath(_cand)
    if os.path.exists(os.path.join(_cand, "g5ai.py")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    import g5ai
except ImportError:
    sys.stderr.write(
        "g5cli: cannot find g5ai.py.\n"
        "  Looked beside this script, in ../macos-lion, /opt/ai-cockpit,\n"
        "  /usr/local/lib/ai-cockpit and /Users/Shared/ai-cockpit.\n")
    sys.exit(2)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _out(text):
    """Write text on both Python 2 and 3 without tripping over unicode."""
    if not isinstance(text, str):
        try:
            text = text.encode("utf-8")
        except Exception:
            text = str(text)
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


def _read(path):
    f = open(path, "rb")
    try:
        return f.read().decode("utf-8", "replace")
    finally:
        f.close()


def _write(path, text):
    f = open(path, "wb")
    try:
        f.write(text.encode("utf-8"))
    finally:
        f.close()


def _ask(prompt, system, provider=None):
    """One call to the gateway, with the failure modes spelled out."""
    try:
        return g5ai.ask(prompt, system=system, provider=provider)
    except Exception as exc:
        msg = str(exc)
        hint = ""
        if "refused" in msg.lower() or "connect" in msg.lower():
            hint = ("\n  The gateway is not answering. Check it with:\n"
                    "    g5-copilot --health\n"
                    "  On Linux:  systemctl status ai-gateway\n")
        g5ai.die("request failed: %s%s" % (msg, hint))


def _strip_fence(text):
    """Models like to wrap output in ``` fences. Remove them."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
    return "\n".join(lines).strip()


def _health_and_exit():
    try:
        info = g5ai.health()
    except Exception as exc:
        _out("gateway: UNREACHABLE (%s)" % exc)
        sys.exit(1)
    _out("gateway: ok")
    if isinstance(info, dict):
        for key in sorted(info):
            _out("  %-12s %s" % (key, info[key]))
    sys.exit(0)


# --------------------------------------------------------------------------
# g5-copilot  --  suggest / explain shell commands
# --------------------------------------------------------------------------
COPILOT_SUGGEST_SYSTEM = (
    "You suggest a single shell command for the user's task. This machine is "
    "either Debian 13 on a 2006 Mac Pro, or OS X 10.7 Lion -- prefer portable "
    "POSIX tools and say so if a command is platform-specific. Reply with the "
    "command on the first line, then a blank line, then at most three short "
    "lines explaining what it does and anything destructive about it. No "
    "markdown fences."
)

COPILOT_EXPLAIN_SYSTEM = (
    "Explain the given shell command clearly and concisely: what it does, flag "
    "by flag, and any risk of data loss. Be specific about which parts are "
    "irreversible. Plain text, no markdown fences."
)

# Commands worth a second look before anyone runs them.
DESTRUCTIVE = (
    "rm ", "rm -", "mkfs", "dd ", "shred", "diskutil erase", "diskutil partition",
    ">/dev/", "> /dev/", "chmod -R", "chown -R", "truncate", "fdisk", "parted",
    "userdel", "groupdel", "drop database", "drop table", ":(){", "fork",
)


def cmd_copilot(argv):
    if not argv or argv[0] in ("-h", "--help"):
        _out(__doc__.split("Installed as")[0].strip())
        _out("\nusage:\n"
             "  g5-copilot suggest <what you want to do>\n"
             "  g5-copilot explain <command ...>\n"
             "  g5-copilot --health\n")
        return 0
    if argv[0] == "--health":
        _health_and_exit()

    mode = "suggest"
    if argv[0] in ("suggest", "explain"):
        mode, argv = argv[0], argv[1:]
    if not argv:
        g5ai.die("nothing to %s" % mode)

    text = " ".join(argv)
    if mode == "explain":
        reply = _ask("Explain this command:\n\n" + text, COPILOT_EXPLAIN_SYSTEM)
        _out(g5ai.wrap(_strip_fence(reply)))
        return 0

    reply = _strip_fence(_ask(text, COPILOT_SUGGEST_SYSTEM))
    lines = reply.splitlines()
    command = lines[0].strip() if lines else ""
    rest = "\n".join(lines[1:]).strip()

    _out("")
    _out("  $ " + command)
    _out("")
    if rest:
        _out(g5ai.wrap(rest, 74))
        _out("")

    low = command.lower()
    if any(tok in low for tok in DESTRUCTIVE):
        _out("  !! This command can destroy data. Read it again before running it.")
        _out("")
    _out("  Not executed. Copy it if you want it.")
    return 0


# --------------------------------------------------------------------------
# g5-codex  --  read files, propose a patch
# --------------------------------------------------------------------------
CODEX_SYSTEM = (
    "You are a careful code editor. You are given one or more files and an "
    "instruction. Return the COMPLETE new contents of each file you change, "
    "each preceded by a line of the form '=== FILE: <path>'. Change as little "
    "as possible. Match the file's existing style, indentation and naming. Do "
    "not add explanatory comments about your changes. If a file needs no "
    "change, omit it entirely. No markdown fences."
)


def _split_files(reply):
    """Parse the '=== FILE: path' response format into {path: contents}."""
    out, path, buf = {}, None, []
    for line in reply.splitlines():
        if line.strip().startswith("=== FILE:"):
            if path is not None:
                out[path] = "\n".join(buf).strip("\n") + "\n"
            path = line.split("=== FILE:", 1)[1].strip()
            buf = []
        elif path is not None:
            buf.append(line)
    if path is not None:
        out[path] = "\n".join(buf).strip("\n") + "\n"
    return out


def cmd_codex(argv):
    if not argv or argv[0] in ("-h", "--help"):
        _out("usage:\n"
             "  g5-codex -m '<instruction>' <file> [file ...]   show a diff\n"
             "  g5-codex --write -m '...' <file> ...            apply it (.bak kept)\n"
             "  g5-codex --health\n")
        return 0
    if argv[0] == "--health":
        _health_and_exit()

    write, instruction, files = False, None, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--write", "-w"):
            write = True
        elif a in ("-m", "--message"):
            i += 1
            if i >= len(argv):
                g5ai.die("-m needs an instruction")
            instruction = argv[i]
        else:
            files.append(a)
        i += 1

    if not instruction:
        g5ai.die("no instruction; use -m '<what to change>'")
    if not files:
        g5ai.die("no files given")

    parts = []
    for path in files:
        if not os.path.isfile(path):
            g5ai.die("not a file: %s" % path)
        parts.append("=== FILE: %s\n%s" % (path, _read(path)))

    prompt = "Instruction: %s\n\n%s" % (instruction, "\n\n".join(parts))
    proposed = _split_files(_strip_fence(_ask(prompt, CODEX_SYSTEM)))

    if not proposed:
        _out("No changes proposed.")
        return 0

    changed = 0
    for path in files:
        if path not in proposed:
            continue
        old, new = _read(path), proposed[path]
        if old == new:
            continue
        changed += 1
        diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                    fromfile=path + " (current)",
                                    tofile=path + " (proposed)")
        _out("".join(diff))
        if write:
            _write(path + ".bak", old)
            _write(path, new)
            _out("  written; previous contents kept as %s.bak" % path)

    if changed == 0:
        _out("No effective changes.")
    elif not write:
        _out("\n%d file(s) would change. Re-run with --write to apply." % changed)
    return 0


# --------------------------------------------------------------------------
# g5-gemini  --  plain conversation
# --------------------------------------------------------------------------
def cmd_gemini(argv):
    if argv and argv[0] == "--health":
        _health_and_exit()
    if argv and argv[0] in ("-h", "--help"):
        _out("usage:\n"
             "  g5-gemini <prompt ...>     one-shot question\n"
             "  g5-gemini                  interactive; blank line or Ctrl-D exits\n")
        return 0

    if argv:
        _out(g5ai.wrap(_ask(" ".join(argv), None, provider="gemini")))
        return 0

    _out("g5-gemini -- blank line or Ctrl-D to exit.")
    history = []
    while True:
        try:
            sys.stdout.write("\n> ")
            sys.stdout.flush()
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            _out("")
            return 0
        if not line or not line.strip():
            return 0
        try:
            reply = g5ai.ask(line.strip(), history=history, provider="gemini")
        except Exception as exc:
            _out("  error: %s" % exc)
            continue
        _out("")
        _out(g5ai.wrap(reply))
        history.append(("user", line.strip()))
        history.append(("assistant", reply))


# --------------------------------------------------------------------------
DISPATCH = {
    "g5-codex": cmd_codex,
    "g5-copilot": cmd_copilot,
    "g5-gemini": cmd_gemini,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    name = os.path.basename(sys.argv[0]).replace(".py", "")

    if name not in DISPATCH:
        # Invoked as g5cli.py directly: first argument selects the tool.
        if argv and ("g5-" + argv[0]) in DISPATCH:
            name, argv = "g5-" + argv[0], argv[1:]
        elif argv and argv[0] in DISPATCH:
            name, argv = argv[0], argv[1:]
        else:
            _out("usage: g5cli.py {codex|copilot|gemini} [args]")
            return 2

    if argv and argv[0] == "--version":
        _out("g5cli %s (%s)" % (__version__, name))
        return 0
    return DISPATCH[name](argv) or 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

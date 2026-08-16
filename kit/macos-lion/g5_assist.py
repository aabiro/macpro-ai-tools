#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
g5-assist -- say what you want in English, get a safe shell command back.

    g5-assist "show me the 10 biggest files in my home folder"
    g5-assist "how much free disk space is there"

The command is shown to you and explained. Nothing runs until you type "y".

Safety notes
------------
This asks a model for a command, and models are sometimes wrong. Two guards:

  1. Nothing is ever executed without you confirming it.
  2. Commands matching known-destructive patterns are refused outright and
     never offered, even if you confirm.

The second guard is deliberately blunt. It will occasionally refuse something
harmless. That is the correct trade for a machine whose owner may be pasting
suggestions they cannot yet evaluate.
"""

import re
import subprocess
import sys

import g5ai

SYSTEM_PROMPT = """\
You translate plain English into a single shell command for Mac OS X 10.7 Lion.

Constraints:
- bash 3.2, BSD userland. NOT GNU coreutils. No --long-gnu-only flags.
- Assume no Homebrew and no developer tools are installed.
- Produce exactly ONE command line. No pipelines spanning multiple lines.
- Prefer read-only commands. Never destructive ones.

Reply in exactly this format and nothing else:

COMMAND: <the command>
EXPLAIN: <one sentence describing what it does>
"""

# Patterns we refuse to run regardless of confirmation. Kept intentionally
# broad -- a false refusal costs a retype, a false pass can cost the machine.
DANGEROUS = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*[rf]", "deletes files recursively/forcibly"),
    (r"\bmkfs|\bnewfs|\bdiskutil\s+(erase|partition|reformat)", "erases or repartitions a disk"),
    (r"\bdd\b.*\bof=/dev/", "writes directly to a raw device"),
    (r">\s*/dev/[sr]?disk", "writes directly to a raw device"),
    (r"\bchmod\s+(-R\s+)?777\s+/", "opens up permissions on system paths"),
    (r"\bchown\s+-R\s+.*\s+/(\s|$)", "changes ownership of the whole filesystem"),
    (r":\(\)\s*\{.*\|.*&\s*\}\s*;?\s*:", "fork bomb"),
    (r"\bshutdown\b|\breboot\b|\bhalt\b", "powers off or restarts the machine"),
    (r"\bkillall\s+-9\b", "force-kills processes broadly"),
    (r"\bcurl\b.*\|\s*(sh|bash)|\bwget\b.*\|\s*(sh|bash)", "pipes the internet into a shell"),
    (r"\bsudo\b", "runs with administrator privileges"),
    (r"/System/|/Library/LaunchDaemons", "modifies system directories"),
]


def screen(command):
    """Return a refusal reason, or None if the command looks acceptable."""
    for pattern, reason in DANGEROUS:
        if re.search(pattern, command, re.IGNORECASE):
            return reason
    return None


def parse(reply):
    command, explain = "", ""
    for line in reply.splitlines():
        line = line.strip()
        if line.upper().startswith("COMMAND:"):
            command = line.split(":", 1)[1].strip().strip("`")
        elif line.upper().startswith("EXPLAIN:"):
            explain = line.split(":", 1)[1].strip()
    if not command:
        # Model ignored the format; fall back to the first non-empty line
        # that looks like a command rather than prose.
        for line in reply.splitlines():
            line = line.strip().strip("`")
            if line and not line.endswith(".") and " " in line:
                command = line
                break
    return command, explain


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 0

    request = " ".join(argv)
    sys.stderr.write("Thinking ...\n")
    try:
        reply = g5ai.ask(request, system=SYSTEM_PROMPT, max_tokens=400)
    except g5ai.G5Error as exc:
        g5ai.die(str(exc))

    command, explain = parse(reply)
    if not command:
        print("Could not get a usable command back. The model said:\n")
        print(g5ai.wrap(reply))
        return 1

    print("")
    print("  Command:  %s" % command)
    if explain:
        print("  Does:     %s" % explain)
    print("")

    reason = screen(command)
    if reason:
        print("REFUSED: this command %s." % reason)
        print("It will not be run. If you genuinely need it, type it yourself")
        print("so the decision is unambiguously yours.")
        return 2

    try:
        answer = raw_input("Run it? [y/N] ").strip().lower()
    except EOFError:
        answer = ""
    if answer not in ("y", "yes"):
        print("Not run.")
        return 0

    print("")
    proc = subprocess.Popen(command, shell=True)
    proc.communicate()
    return proc.returncode or 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.stderr.write("\nCancelled.\n")
        sys.exit(130)

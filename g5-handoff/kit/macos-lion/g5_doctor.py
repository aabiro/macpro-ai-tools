#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
g5-doctor -- "The Custodian". Have an AI read this Mac's vital signs.

    g5-doctor              analyse the machine and print a verdict
    g5-doctor --raw        just dump the diagnostics, no AI, no network
    g5-doctor --save FILE  also write the raw diagnostics to FILE

This gathers SMART disk status, ECC memory health, thermals, load and panic
reports, then asks a model to interpret them the way a technician would.

Everything it collects works without administrator rights. If you run it from
an admin account it additionally includes /var/log/system.log.
"""

import sys

import g5ai

SYSTEM_PROMPT = """\
You are a senior Apple hardware technician who has serviced Mac Pro towers since
2006. You are looking at a diagnostic snapshot from a Mac Pro 1,1 (2006, dual
Xeon 5150, FB-DIMM memory, mechanical drives) running Mac OS X 10.7 Lion.

Report in this exact structure, in plain language a non-technical owner can act on:

VERDICT: one line - HEALTHY, WATCH, or ATTENTION NEEDED

FINDINGS: the specific things you can actually see in the data. Quote the numbers.
If something looks fine, say so briefly rather than padding.

WATCH LIST: known age-related failure points for this exact model that the data
does not disprove - FB-DIMM failure (they run hot and fail with ECC errors),
power supply ageing, dust-clogged thermal paths, and mechanical drives past
their service life.

DO THIS NEXT: concrete steps, most important first. Be specific.

Do not invent readings that are not in the data. If a section is missing, say
that it was not available rather than guessing.
"""


def main(argv):
    raw_only = "--raw" in argv
    save_path = None
    if "--save" in argv:
        idx = argv.index("--save")
        if idx + 1 >= len(argv):
            g5ai.die("--save needs a filename")
        save_path = argv[idx + 1]

    sys.stderr.write("Collecting diagnostics from this Mac ...\n")
    report = g5ai.collect_diagnostics()

    if save_path:
        try:
            handle = open(save_path, "wb")
            try:
                handle.write(report.encode("utf-8"))
            finally:
                handle.close()
            sys.stderr.write("Raw diagnostics written to %s\n" % save_path)
        except (IOError, OSError) as exc:
            sys.stderr.write("Could not write %s: %s\n" % (save_path, exc))

    if raw_only:
        print(report)
        return 0

    sys.stderr.write("Asking the model to interpret them ...\n\n")
    try:
        verdict = g5ai.ask(report, system=SYSTEM_PROMPT, max_tokens=1500)
    except g5ai.G5Error as exc:
        sys.stderr.write(str(exc) + "\n\n")
        sys.stderr.write(
            "Tip: you can still see the raw numbers without any network:\n"
            "    g5-doctor --raw\n"
        )
        return 1

    print("=" * 72)
    print(" MAC PRO HEALTH REPORT")
    print("=" * 72)
    print("")
    print(g5ai.wrap(verdict))
    print("")
    print("=" * 72)
    print("(Raw data: g5-doctor --raw)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)

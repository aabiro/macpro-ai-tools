#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
retro-port -- back-port modern source code so it builds on this machine.

    retro-port modern.c                 write modern_retro.c next to it
    retro-port app.py --lang python     target Lion's Python 2.7.1
    retro-port modern.c -o out.c        choose the output name
    retro-port modern.c --print         print to screen, write nothing

A note on what this machine actually is
---------------------------------------
The original project plan described a PowerPC G5 and asked for AltiVec
intrinsics. This machine is NOT a PowerPC G5 -- it is a Mac Pro 1,1 with Intel
Xeon 5150 processors. The correct vector instruction set here is SSE/SSE2/SSSE3,
not AltiVec, and the correct architecture flags are x86_64/i386.

Also note: no compiler is installed by default. To actually build the C output
you need Xcode 4.6.3, the last version supporting Lion. See
/Users/Shared/ai-cockpit/README.md.
"""

import os
import sys

import g5ai

TARGETS = {
    "c": """\
Rewrite the supplied C/C++ so it compiles cleanly on Mac OS X 10.7 Lion with
Xcode 4.6.3 (Clang 4.2 / LLVM-GCC 4.2, C99 and C++03 -- NOT C++11).

Target hardware: Mac Pro 1,1, Intel Xeon 5150 (Core micro-architecture, x86_64).
Vector extensions available: SSE, SSE2, SSE3, SSSE3. NOT SSE4.2, NOT AVX.
This is an Intel machine, so do NOT emit AltiVec or any PowerPC intrinsics.

Rules:
- Replace C++11 and later constructs (auto, nullptr, range-for, lambdas,
  std::unique_ptr, constexpr, threads) with C++03 equivalents.
- Replace POSIX-2008-only or Linux-only calls with BSD/Darwin equivalents.
- Keep behaviour identical. Do not silently drop functionality.
- If something genuinely cannot be back-ported, leave it in place and mark it
  with a comment beginning: // RETRO-PORT:
""",
    "python": """\
Rewrite the supplied Python so it runs on Python 2.7.1, the interpreter that
ships with Mac OS X 10.7 Lion.

Rules:
- No f-strings; use % formatting.
- print as a statement, or add: from __future__ import print_function
- urllib.request -> urllib2. pathlib -> os.path. subprocess.run -> Popen.
- No type annotations, no dataclasses, no enum, no typing module.
- STANDARD LIBRARY ONLY. This machine cannot install packages -- its TLS is too
  old to reach PyPI. If the code needs a third-party package, do not pretend it
  is available; leave it and mark with a comment beginning: # RETRO-PORT:
- Keep behaviour identical.
""",
    "shell": """\
Rewrite the supplied shell script so it runs under bash 3.2 with the BSD
userland on Mac OS X 10.7 Lion.

Rules:
- No associative arrays, no ${var^^}, no mapfile, no |& -- these need bash 4.
- BSD tool flags, not GNU: sed -i needs an argument, stat/date/readlink differ.
- Assume no Homebrew and no GNU coreutils.
- Keep behaviour identical. Mark anything impossible with: # RETRO-PORT:
""",
}

EXT_HINTS = {
    ".c": "c", ".h": "c", ".cc": "c", ".cpp": "c", ".cxx": "c", ".hpp": "c", ".m": "c",
    ".py": "python",
    ".sh": "shell", ".bash": "shell",
}

INSTRUCTION_TAIL = """

Output ONLY the rewritten source code. No explanation before or after it, and
no markdown code fences.
"""


def strip_fences(text):
    """Models sometimes wrap output in ``` fences despite instructions."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
    return "\n".join(lines)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0

    args = list(argv)
    lang = None
    out_path = None
    to_screen = False

    for flag, attr in (("--lang", "lang"), ("-o", "out")):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 >= len(args):
                g5ai.die("%s needs a value" % flag)
            value = args[idx + 1]
            del args[idx:idx + 2]
            if attr == "lang":
                lang = value.lower()
            else:
                out_path = value

    if "--print" in args:
        to_screen = True
        args.remove("--print")

    if not args:
        g5ai.die("Which file should I port? Try: retro-port myfile.c")

    src_path = args[0]
    if not os.path.isfile(src_path):
        g5ai.die("No such file: %s" % src_path)

    try:
        handle = open(src_path, "rb")
        try:
            source = handle.read().decode("utf-8", "replace")
        finally:
            handle.close()
    except (IOError, OSError) as exc:
        g5ai.die("Could not read %s: %s" % (src_path, exc))

    if not source.strip():
        g5ai.die("%s is empty" % src_path)

    if not lang:
        lang = EXT_HINTS.get(os.path.splitext(src_path)[1].lower(), "c")
    if lang not in TARGETS:
        g5ai.die("Unknown language %r. Choose one of: %s"
                 % (lang, ", ".join(sorted(TARGETS))))

    sys.stderr.write("Porting %s (%s) for Lion ...\n" % (src_path, lang))
    system_prompt = TARGETS[lang] + INSTRUCTION_TAIL
    try:
        # Give the model room: output is at least as long as the input.
        budget = max(2048, min(8000, len(source) // 2 + 1500))
        ported = g5ai.ask(source, system=system_prompt, max_tokens=budget)
    except g5ai.G5Error as exc:
        g5ai.die(str(exc))

    ported = strip_fences(ported)

    if to_screen:
        print(ported)
        return 0

    if not out_path:
        root, ext = os.path.splitext(src_path)
        out_path = "%s_retro%s" % (root, ext)

    if os.path.exists(out_path):
        try:
            answer = raw_input("%s exists. Overwrite? [y/N] " % out_path).strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("y", "yes"):
            print("Not written. Use -o to pick another name.")
            return 0

    try:
        handle = open(out_path, "wb")
        try:
            handle.write(ported.encode("utf-8"))
            if not ported.endswith("\n"):
                handle.write(b"\n")
        finally:
            handle.close()
    except (IOError, OSError) as exc:
        g5ai.die("Could not write %s: %s" % (out_path, exc))

    print("Wrote %s" % out_path)

    flagged = [ln for ln in ported.splitlines() if "RETRO-PORT:" in ln]
    if flagged:
        print("")
        print("The model could not fully port %d item(s):" % len(flagged))
        for line in flagged[:10]:
            print("  %s" % line.strip()[:100])
        print("")
        print("Review these by hand before building.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)

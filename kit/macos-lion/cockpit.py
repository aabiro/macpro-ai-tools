#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cockpit -- the AI Cockpit for this Mac Pro. A full-screen terminal interface.

Run it with:    cockpit

Screens:
    1  Oracle      talk to a model
    2  Custodian   have the machine's health read and explained
    3  Retro-Coder back-port a source file so it builds here
    4  Status      gateway, provider, model, and how to change them
    Q  Quit

Python 2.7 standard library only. Works over SSH and on the local console.
"""

import curses
import os
import sys
import textwrap

import g5ai

BANNER = "AI COCKPIT"


# ---------------------------------------------------------------------------
# curses helpers
# ---------------------------------------------------------------------------


def safe_addstr(win, row, col, text, attr=0):
    """addstr that refuses to blow up at screen edges.

    curses raises if you write to the very last cell of the window, and Lion's
    terminal sizes vary. Clipping here keeps the UI from crashing mid-session.
    """
    height, width = win.getmaxyx()
    if row < 0 or row >= height or col < 0 or col >= width:
        return
    space = width - col - 1
    if space <= 0:
        return
    try:
        win.addstr(row, col, text[:space], attr)
    except curses.error:
        pass


def layout(text, width):
    """Wrap text to width, preserving paragraph breaks."""
    lines = []
    for para in (text or "").split("\n"):
        if not para.strip():
            lines.append("")
        else:
            lines.extend(textwrap.wrap(para, max(20, width)) or [""])
    return lines


def draw_frame(win, title, subtitle=""):
    height, width = win.getmaxyx()
    win.erase()
    header = " %s :: %s " % (BANNER, title)
    safe_addstr(win, 0, 0, header.ljust(width - 1),
                curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
    if subtitle:
        safe_addstr(win, 1, 1, subtitle[:width - 2], curses.color_pair(4) | curses.A_DIM)
    return height, width


def footer(win, text):
    height, width = win.getmaxyx()
    safe_addstr(win, height - 1, 0, (" " + text).ljust(width - 1),
                curses.color_pair(1) | curses.A_REVERSE)


def prompt_line(win, row, label):
    """Read a line of text from the user at a given row."""
    height, width = win.getmaxyx()
    safe_addstr(win, row, 1, label, curses.color_pair(2) | curses.A_BOLD)
    win.move(row, min(len(label) + 2, width - 2))
    curses.echo()
    curses.curs_set(1)
    try:
        raw = win.getstr(row, len(label) + 2, max(10, width - len(label) - 4))
    except curses.error:
        raw = ""
    finally:
        curses.noecho()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
    return (raw or "").strip()


def show_busy(win, message):
    height, width = win.getmaxyx()
    safe_addstr(win, height - 2, 1, (message + " ").ljust(width - 3),
                curses.color_pair(4) | curses.A_BOLD)
    win.refresh()


def show_scrollable(win, title, subtitle, body, extra_keys=""):
    """Display long text with arrow-key scrolling. Returns the key that exited."""
    offset = 0
    while True:
        height, width = draw_frame(win, title, subtitle)
        lines = layout(body, width - 4)
        view_height = max(1, height - 4)
        offset = max(0, min(offset, max(0, len(lines) - view_height)))

        for i in range(view_height):
            idx = offset + i
            if idx >= len(lines):
                break
            safe_addstr(win, 2 + i, 2, lines[idx], curses.color_pair(3))

        more = ""
        if len(lines) > view_height:
            pct = int(100.0 * (offset + view_height) / max(1, len(lines)))
            more = "  [%d%%  up/down to scroll]" % min(100, pct)
        footer(win, "B back   Q quit%s%s" % (("   " + extra_keys) if extra_keys else "", more))
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_DOWN, ord('j')):
            offset += 1
        elif key in (curses.KEY_UP, ord('k')):
            offset -= 1
        elif key == curses.KEY_NPAGE or key == ord(' '):
            offset += view_height
        elif key == curses.KEY_PPAGE:
            offset -= view_height
        elif key in (curses.KEY_HOME, ord('g')):
            offset = 0
        elif key in (curses.KEY_END, ord('G')):
            offset = len(lines)
        else:
            return key


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------


def screen_oracle(win, state):
    history = state.setdefault("oracle_history", [])
    status = ""

    while True:
        height, width = draw_frame(
            win, "ORACLE",
            "%s / %s" % (state["cfg"]["provider"], state["model_label"]))

        # Render the conversation from the bottom up so the newest is visible.
        rendered = []
        for msg in history:
            who = "YOU" if msg["role"] == "user" else "AI "
            colour = curses.color_pair(2) if msg["role"] == "user" else curses.color_pair(3)
            for i, line in enumerate(layout(msg["content"], width - 8)):
                rendered.append((("%s  " % who) if i == 0 else "     ", line, colour))

        view_height = max(1, height - 5)
        for i, (prefix, line, colour) in enumerate(rendered[-view_height:]):
            safe_addstr(win, 2 + i, 2, prefix, curses.color_pair(4) | curses.A_DIM)
            safe_addstr(win, 2 + i, 7, line, colour)

        if status:
            safe_addstr(win, height - 3, 2, status[:width - 4],
                        curses.color_pair(5) | curses.A_BOLD)

        footer(win, "Type a message and press Return   /clear  /back  /quit")
        win.refresh()

        text = prompt_line(win, height - 2, ">")
        status = ""

        if not text:
            continue
        lowered = text.lower()
        if lowered in ("/quit", "/q"):
            return "quit"
        if lowered in ("/back", "/b"):
            return "menu"
        if lowered == "/clear":
            del history[:]
            continue

        show_busy(win, "Thinking ...")
        try:
            reply = g5ai.ask(
                text,
                system=("You are the Oracle, answering on a 2006 Mac Pro terminal "
                        "running Mac OS X Lion. Be concise and concrete. Plain text "
                        "only -- no markdown, no code fences, no emoji, because this "
                        "is an 80-column terminal."),
                history=history[-12:],
                cfg=state["cfg"],
            )
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": reply})
        except g5ai.G5Error as exc:
            status = str(exc).splitlines()[0][:width - 6]
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": str(exc)})


def screen_custodian(win, state):
    draw_frame(win, "CUSTODIAN", "reading this machine's vital signs")
    show_busy(win, "Collecting diagnostics ...")
    report = g5ai.collect_diagnostics()

    if state.get("custodian_verdict") is None:
        show_busy(win, "Asking the model to interpret them ...")
        try:
            state["custodian_verdict"] = g5ai.ask(
                report, system=CUSTODIAN_PROMPT, max_tokens=1500, cfg=state["cfg"])
        except g5ai.G5Error as exc:
            state["custodian_verdict"] = str(exc)

    while True:
        key = show_scrollable(
            win, "CUSTODIAN", "health verdict",
            state["custodian_verdict"], extra_keys="R re-scan   D raw data")
        if key in (ord('q'), ord('Q')):
            return "quit"
        if key in (ord('b'), ord('B'), 27):
            return "menu"
        if key in (ord('r'), ord('R')):
            state["custodian_verdict"] = None
            return screen_custodian(win, state)
        if key in (ord('d'), ord('D')):
            sub = show_scrollable(win, "CUSTODIAN", "raw diagnostics", report)
            if sub in (ord('q'), ord('Q')):
                return "quit"


CUSTODIAN_PROMPT = """\
You are a senior Apple hardware technician who has serviced Mac Pro towers since
2006. You are reading a diagnostic snapshot from a Mac Pro 1,1 (2006, dual Xeon
5150, FB-DIMM memory, mechanical drives) running Mac OS X 10.7 Lion.

Structure your answer exactly as:

VERDICT: one line - HEALTHY, WATCH, or ATTENTION NEEDED

FINDINGS: what you can actually see in the data, quoting the numbers.

WATCH LIST: age-related failure points for this model the data does not
disprove - FB-DIMM failure, power supply ageing, dust and thermal paths,
mechanical drives past service life.

DO THIS NEXT: concrete steps, most important first.

Plain text only, no markdown, 78 columns max. Do not invent readings.
"""


def screen_retro(win, state):
    status = ""
    while True:
        height, width = draw_frame(win, "RETRO-CODER",
                                   "back-port a source file so it builds here")
        blurb = [
            "Give me a path to a source file and I will rewrite it to build on",
            "this machine: Mac OS X 10.7 Lion, Intel Xeon (SSE/SSE2/SSSE3),",
            "Clang 4.2 / C++03, Python 2.7, bash 3.2.",
            "",
            "The rewritten file is saved alongside the original with a _retro",
            "suffix. The original is never modified.",
            "",
            "Example:   /Users/Shared/example.c",
        ]
        for i, line in enumerate(blurb):
            safe_addstr(win, 2 + i, 2, line, curses.color_pair(3))

        if status:
            for i, line in enumerate(layout(status, width - 4)[:6]):
                safe_addstr(win, 3 + len(blurb) + i, 2, line,
                            curses.color_pair(5))

        footer(win, "Enter a file path   /back   /quit")
        win.refresh()

        path = prompt_line(win, height - 2, "file>")
        if not path:
            continue
        if path.lower() in ("/quit", "/q"):
            return "quit"
        if path.lower() in ("/back", "/b"):
            return "menu"

        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            status = "No such file: %s" % path
            continue

        try:
            handle = open(path, "rb")
            try:
                source = handle.read().decode("utf-8", "replace")
            finally:
                handle.close()
        except (IOError, OSError) as exc:
            status = "Could not read it: %s" % exc
            continue

        if not source.strip():
            status = "That file is empty."
            continue

        ext = os.path.splitext(path)[1].lower()
        lang = {".py": "python", ".sh": "shell", ".bash": "shell"}.get(ext, "c")

        show_busy(win, "Porting %s ..." % os.path.basename(path))
        try:
            import retro_port
            budget = max(2048, min(8000, len(source) // 2 + 1500))
            ported = retro_port.strip_fences(g5ai.ask(
                source,
                system=retro_port.TARGETS[lang] + retro_port.INSTRUCTION_TAIL,
                max_tokens=budget,
                cfg=state["cfg"],
            ))
        except g5ai.G5Error as exc:
            status = str(exc)
            continue

        root, ext2 = os.path.splitext(path)
        out_path = "%s_retro%s" % (root, ext2)
        try:
            handle = open(out_path, "wb")
            try:
                handle.write(ported.encode("utf-8"))
            finally:
                handle.close()
            status = "Wrote %s" % out_path
        except (IOError, OSError) as exc:
            status = "Could not write %s: %s" % (out_path, exc)
            continue

        key = show_scrollable(win, "RETRO-CODER", "wrote %s" % out_path, ported)
        if key in (ord('q'), ord('Q')):
            return "quit"


def screen_status(win, state):
    cfg = g5ai.load_config()
    state["cfg"] = cfg

    lines = []
    lines.append("Gateway    : %s" % (cfg["gateway"] or "(not set)"))
    lines.append("Provider   : %s" % cfg["provider"])
    lines.append("Model      : %s" % (cfg["model"] or "(gateway default)"))
    lines.append("Max tokens : %s" % cfg["max_tokens"])
    lines.append("")

    if not cfg["gateway"]:
        lines.append(g5ai.NO_GATEWAY_MESSAGE)
    else:
        show_busy(win, "Checking the gateway ...")
        try:
            info = g5ai.health(cfg)
            ready = info.get("providers_configured") or []
            lines.append("Gateway is REACHABLE (version %s)" % info.get("version", "?"))
            lines.append("Providers with keys: %s" % (", ".join(ready) if ready else "NONE"))
            if cfg["provider"] not in ready and ready:
                lines.append("")
                lines.append("Your provider '%s' has no key on the gateway."
                             % cfg["provider"])
                lines.append("Change it from Terminal with:")
                lines.append("    g5-config set provider %s" % ready[0])
        except g5ai.G5Error as exc:
            lines.append("Gateway is NOT REACHABLE")
            lines.append("")
            lines.append(str(exc))

    lines.append("")
    lines.append("-" * 60)
    lines.append("Change settings from Terminal:")
    lines.append("    g5-config show")
    lines.append("    g5-config set gateway http://192.168.1.50:8081")
    lines.append("    g5-config set provider gemini")
    lines.append("    g5-config test")
    lines.append("")
    lines.append("Full instructions: /Users/Shared/ai-cockpit/README.md")

    key = show_scrollable(win, "STATUS", "configuration and connectivity",
                          "\n".join(lines))
    return "quit" if key in (ord('q'), ord('Q')) else "menu"


def screen_menu(win, state):
    cfg = state["cfg"]
    reachable = state.get("reachable")

    while True:
        height, width = draw_frame(win, "MAIN MENU",
                                   "Mac Pro 1,1  //  Mac OS X 10.7 Lion")

        art = [
            "",
            "   This Mac is too old to talk to modern AI services directly.",
            "   It reaches them through a small gateway program running on a",
            "   newer computer on your network.",
            "",
        ]
        for i, line in enumerate(art):
            safe_addstr(win, 2 + i, 2, line, curses.color_pair(4) | curses.A_DIM)

        items = [
            ("1", "Oracle", "ask a model anything"),
            ("2", "Custodian", "check this machine's health"),
            ("3", "Retro-Coder", "back-port code to build here"),
            ("4", "Status", "gateway and settings"),
            ("Q", "Quit", ""),
        ]
        row = 2 + len(art) + 1
        for key, name, desc in items:
            safe_addstr(win, row, 4, "[%s]" % key,
                        curses.color_pair(4) | curses.A_BOLD)
            safe_addstr(win, row, 9, name.ljust(14), curses.color_pair(3) | curses.A_BOLD)
            safe_addstr(win, row, 24, desc, curses.color_pair(4) | curses.A_DIM)
            row += 1

        row += 1
        if not cfg["gateway"]:
            safe_addstr(win, row, 4,
                        "No gateway configured yet -- press 4 for setup steps.",
                        curses.color_pair(5) | curses.A_BOLD)
        elif reachable is False:
            safe_addstr(win, row, 4,
                        "Gateway %s is not responding -- press 4." % cfg["gateway"],
                        curses.color_pair(5) | curses.A_BOLD)
        elif reachable:
            safe_addstr(win, row, 4, "Gateway online: %s" % cfg["gateway"],
                        curses.color_pair(3))

        footer(win, "Press a number, or Q to quit")
        win.refresh()

        key = win.getch()
        if key in (ord('q'), ord('Q')):
            return "quit"
        if key == ord('1'):
            return "oracle"
        if key == ord('2'):
            return "custodian"
        if key == ord('3'):
            return "retro"
        if key == ord('4'):
            return "status"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main(stdscr):
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    curses.init_pair(1, curses.COLOR_CYAN, bg)
    curses.init_pair(2, curses.COLOR_YELLOW, bg)
    curses.init_pair(3, curses.COLOR_GREEN, bg)
    curses.init_pair(4, curses.COLOR_WHITE, bg)
    curses.init_pair(5, curses.COLOR_RED, bg)
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    state = {"cfg": g5ai.load_config()}
    state["model_label"] = state["cfg"]["model"] or "default"
    state["custodian_verdict"] = None

    # One quick reachability probe so the menu can tell the truth up front.
    if state["cfg"]["gateway"]:
        try:
            g5ai.health(state["cfg"])
            state["reachable"] = True
        except g5ai.G5Error:
            state["reachable"] = False
    else:
        state["reachable"] = None

    where = "menu"
    while True:
        if where == "menu":
            where = screen_menu(stdscr, state)
        elif where == "oracle":
            where = screen_oracle(stdscr, state)
        elif where == "custodian":
            where = screen_custodian(stdscr, state)
        elif where == "retro":
            where = screen_retro(stdscr, state)
        elif where == "status":
            where = screen_status(stdscr, state)
            state["model_label"] = state["cfg"]["model"] or "default"
            state["reachable"] = None
            if state["cfg"]["gateway"]:
                try:
                    g5ai.health(state["cfg"])
                    state["reachable"] = True
                except g5ai.G5Error:
                    state["reachable"] = False
        elif where == "quit":
            return
        else:
            where = "menu"


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except curses.error as exc:
        sys.stderr.write(
            "The terminal could not start the full-screen interface: %s\n"
            "Try a larger window, or use the command-line tools instead:\n"
            "    g5-doctor    g5-assist \"...\"    retro-port FILE\n" % exc)
        sys.exit(1)

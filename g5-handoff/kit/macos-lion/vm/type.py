#!/usr/bin/env python3
"""Type a line into the VM console via the QEMU monitor, then verify by screenshot.

Single-user mode has no network and no shared folder, so the only way in is the
keyboard. sendkey takes one key at a time, so translate the string here.
"""
import socket, sys, time

PLAIN = {
    "/": "slash", "-": "minus", ".": "dot", " ": "spc", "=": "equal",
    ";": "semicolon", "'": "apostrophe", ",": "comma", "\\": "backslash",
    "[": "bracket_left", "]": "bracket_right", "`": "grave_accent",
}
SHIFTED = {
    "_": "minus", ":": "semicolon", '"': "apostrophe", ">": "dot", "<": "comma",
    "|": "backslash", "?": "slash", "+": "equal", "{": "bracket_left",
    "}": "bracket_right", "~": "grave_accent",
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
}

def keys_for(ch):
    if ch == "\n":                       return ["ret"]
    if ch == "\t":                       return ["tab"]
    if ch.islower() or ch.isdigit():     return [ch]
    if ch.isupper():                     return ["shift-" + ch.lower()]
    if ch in PLAIN:                      return [PLAIN[ch]]
    if ch in SHIFTED:                    return ["shift-" + SHIFTED[ch]]
    raise SystemExit("no key mapping for %r" % ch)

def main():
    text = sys.argv[1]
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect("/tmp/lion-monitor")
    time.sleep(0.4)
    try: s.recv(65536)
    except Exception: pass
    n = 0
    for ch in text:
        for k in keys_for(ch):
            s.sendall(("sendkey %s\n" % k).encode())
            n += 1
            time.sleep(0.06)           # the guest console needs a moment per key
            try: reply = s.recv(65536).decode("utf-8", "replace")
            except Exception: reply = ""
            # A bad key name fails quietly unless the reply is actually read.
            if "unknown" in reply.lower() or "invalid" in reply.lower() \
               or "Error" in reply or "not found" in reply:
                raise SystemExit("    monitor rejected key %r: %s"
                                 % (k, " ".join(reply.split())[:140]))
    s.close()
    print("    typed %d chars (%d keys): %s" % (len(text), n, text.rstrip("\n")))

main()

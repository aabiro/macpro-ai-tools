#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
g5-config -- inspect and change the AI Cockpit's settings.

    g5-config show                              show current settings
    g5-config test                              check the gateway is reachable
    g5-config set gateway http://10.0.0.5:8081  point at a gateway
    g5-config set provider anthropic            gemini | anthropic | openai
    g5-config set model claude-sonnet-5         blank to use gateway default
    g5-config unset model                       go back to the default

Settings are written to ~/.g5ai.json for the current user.
"""

import sys

import g5ai

VALID_KEYS = ("gateway", "provider", "model", "max_tokens", "timeout")
VALID_PROVIDERS = ("gemini", "anthropic", "openai")

USAGE = __doc__.strip()


def cmd_show():
    cfg = g5ai.load_config()
    print("AI Cockpit settings")
    print("-" * 60)
    for key in VALID_KEYS:
        value = cfg.get(key)
        shown = value if (value or value == 0) else "(not set)"
        print("  %-12s %s" % (key, shown))
    print("-" * 60)
    print("  machine-wide file : %s" % g5ai.SYSTEM_CONFIG)
    print("  your file         : %s" % g5ai.USER_CONFIG)
    if not cfg.get("gateway"):
        print("")
        print(g5ai.NO_GATEWAY_MESSAGE)
    return 0


def cmd_test():
    cfg = g5ai.load_config()
    print("Testing gateway at %s ..." % (cfg.get("gateway") or "(not set)"))
    try:
        info = g5ai.health(cfg)
    except g5ai.G5Error as exc:
        print("")
        print("FAILED")
        print("")
        print(str(exc))
        return 1

    ready = info.get("providers_configured") or []
    print("  reachable      : yes")
    print("  gateway version: %s" % info.get("version", "?"))
    print("  providers ready: %s" % (", ".join(ready) if ready else "NONE"))

    if not ready:
        print("")
        print("The gateway is running but has no API keys. On the gateway")
        print("machine, set a key and restart it, for example:")
        print("    export GEMINI_API_KEY=your-key-here")
        return 1

    chosen = cfg.get("provider")
    if chosen not in ready:
        print("")
        print("Note: your provider is set to '%s' but the gateway only has"
              % chosen)
        print("keys for: %s" % ", ".join(ready))
        print("Switch with:  g5-config set provider %s" % ready[0])
        return 1

    print("")
    print("Sending a live test prompt ...")
    try:
        reply = g5ai.ask("Reply with exactly: COCKPIT ONLINE", max_tokens=50, cfg=cfg)
    except g5ai.G5Error as exc:
        print("FAILED")
        print(str(exc))
        return 1
    print("  model replied  : %s" % reply.strip()[:120])
    print("")
    print("All good. Try:  cockpit")
    return 0


def cmd_set(key, value):
    if key not in VALID_KEYS:
        g5ai.die("Unknown setting %r.\nValid settings: %s"
                 % (key, ", ".join(VALID_KEYS)))

    if key == "provider" and value not in VALID_PROVIDERS:
        g5ai.die("Provider must be one of: %s" % ", ".join(VALID_PROVIDERS))

    if key in ("max_tokens", "timeout"):
        try:
            value = int(value)
        except ValueError:
            g5ai.die("%s must be a whole number" % key)

    if key == "gateway" and value and not value.startswith("http"):
        value = "http://" + value

    user_cfg = g5ai._read_json(g5ai.USER_CONFIG)
    user_cfg[key] = value
    g5ai.save_user_config(user_cfg)
    print("Set %s = %s" % (key, value))

    if key == "gateway":
        print("")
        return cmd_test()
    return 0


def cmd_unset(key):
    if key not in VALID_KEYS:
        g5ai.die("Unknown setting %r" % key)
    user_cfg = g5ai._read_json(g5ai.USER_CONFIG)
    if key in user_cfg:
        del user_cfg[key]
        g5ai.save_user_config(user_cfg)
        print("Unset %s" % key)
    else:
        print("%s was not set in your config" % key)
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0

    command = argv[0]
    if command == "show":
        return cmd_show()
    if command == "test":
        return cmd_test()
    if command == "set":
        if len(argv) < 2:
            g5ai.die("Usage: g5-config set <setting> <value>")
        # Allow an empty value, which clears the setting.
        return cmd_set(argv[1], argv[2] if len(argv) > 2 else "")
    if command == "unset":
        if len(argv) < 2:
            g5ai.die("Usage: g5-config unset <setting>")
        return cmd_unset(argv[1])

    g5ai.die("Unknown command %r\n\n%s" % (command, USAGE))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)

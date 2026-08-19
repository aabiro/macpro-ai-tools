# Mac Pro 1,1 — Handover Package

Everything needed to hand a 2006 Mac Pro to a new owner as a clean, documented,
genuinely useful machine — with AI tooling that works for *them*.

## Start here

| If you are… | Read |
|---|---|
| Handing the machine over | [`HANDOFF.md`](HANDOFF.md) — machine truth and verified state |
| Wanting the full build plan | [`IMPLEMENTATION-PLAN.md`](IMPLEMENTATION-PLAN.md) — phased, with what was dropped and why |
| The new owner | [`kit/macos-lion/README.md`](kit/macos-lion/README.md) — also installed on the machine at `/Users/Shared/ai-cockpit/README.md` |
| Installing Linux on it | [`kit/linux/LINUX-STARTER-PACK.md`](kit/linux/LINUX-STARTER-PACK.md) |
| **Linux boots to a black screen** | [`kit/LINUX-BOOT-AND-DISPLAY.md`](kit/LINUX-BOOT-AND-DISPLAY.md) — read this first, it is the one real gotcha |
| **Doing the disk work** | [`kit/PARTITION-RUNBOOK.md`](kit/PARTITION-RUNBOOK.md) + [`kit/BOOT-STEPS.md`](kit/BOOT-STEPS.md) |

## ⚠ Do NOT run the privacy scrub

`kit/scrub/scrub.sh` exists but **must not be run on this handover.**

The machine is going to the person who owns the `administrator` account. Their
Desktop, Documents, Downloads, projects, and `Liferaft` backup are *their own
files* — deleting them is the opposite of what this handover needs.

The script is kept only for a future handover to a *different* person. If that
day comes, read `HANDOFF.md` §6 first.

The one thing worth considering now is the operator SSH key in
`/Users/ai-cockpit/.ssh/authorized_keys`, which grants remote access to whoever
set up the automation. Keep it if you want to keep helping remotely; remove it
if the machine should be fully independent:

```bash
rm /Users/ai-cockpit/.ssh/authorized_keys      # optional, reversible
```

## The problem this package solves

The machine runs Mac OS X 10.7 Lion, whose OpenSSL is from 2010. Modern
services require TLS 1.2+. Measured on the hardware:

```
$ curl -o /dev/null -w '%{http_code}' https://api.anthropic.com
000        # not an HTTP error — no connection at all
```

Two honest fixes, both delivered:

1. **Bridge it.** A gateway on a modern machine performs TLS on the Mac's
   behalf. Working and verified end-to-end.
2. **Replace the OS.** Linux removes the limitation entirely. Documented,
   requires physical media.

## Contents

```
├── HANDOFF.md                     machine truth + verified state + outstanding action
├── IMPLEMENTATION-PLAN.md         phased plan; what was built, dropped, and why
├── g5-ai-integration-plan.md      original plan, unmodified, for the record
├── macpro-omni-server-plan.md     original plan, unmodified, for the record
└── kit/
    ├── gateway/aigw.py            zero-dependency TLS gateway (Python 3 stdlib)
    ├── macos-lion/                installed on the machine — clients, installer, README
    ├── cockpit-web/               Next.js console; drop-in replacement for aigw.py
    ├── linux/                     install guide (EFI32!) + bootstrap.sh
    └── scrub/scrub.sh             privacy scrub — RUN BEFORE SHIPPING
```

## What was verified, not assumed

- All six Python modules compile under Lion's Python 2.7.1
- Live round trip: the Mac Pro received `COCKPIT ONLINE` from a current Gemini
  model — a machine that cannot complete a TLS handshake, holding a conversation
  with a 2026 language model
- The same Mac client works against **both** `aigw.py` and the Next.js app,
  unchanged, confirming the drop-in contract
- `g5-doctor --raw` works with no network at all
- The destructive-command guard was tested independently: 9 dangerous commands
  refused, 3 safe ones allowed
- Machine is bootable, both disks SMART-clean, with three independent boot paths

## Corrections to the original plans

The source plans were written before the hardware was inspected. The
significant one: they describe a **PowerPC Power Mac G5**. It is an **Intel Mac
Pro 1,1**. Every code-generation target changed from AltiVec to SSE. Full list
in `HANDOFF.md` §1.

# Mac Pro 1,1 — Phased Implementation Plan

**Objective:** hand this machine to a new owner as a clean, documented,
genuinely useful computer, with AI tooling that works for *them* rather than
for the network it is leaving.

Status key: **DONE** · **BLOCKED** (needs something I cannot do remotely) ·
**NEW OWNER** (theirs to run, fully documented)

---

## How this plan differs from the two original ones

The source plans were `g5-ai-integration-plan.md` (AI tools for a vintage Mac)
and `macpro-omni-server-plan.md` (turn the machine into a home-lab server).
Both were written before the hardware was inspected. Reconciling them against
reality changed three things:

1. **The hardware is not what the plan said.** Intel Xeon, not PowerPC G5. Every
   code-generation target changed from AltiVec to SSE. (`HANDOFF.md` §1)
2. **The goal inverted.** The omni-server plan integrates the machine *into* the
   previous owner's network — Tailscale exit node, Stripe webhook ingress,
   Grafana scraping `xcelsior`. A handover requires the exact opposite:
   removing every trace of that network. Those phases are dropped, not deferred.
3. **The gateway had to become portable.** The original hardcoded a Tailscale
   IP. For a new owner that address does not exist and cannot be made to exist.

What survives from the originals is the genuinely good idea at their core: a
modern machine performs TLS on behalf of the vintage one, and lightweight
era-appropriate clients do the rest.

---

## Phase 0 — Establish ground truth · **DONE**

Nothing can be planned against assumptions on a nineteen-year-old machine.

| Step | Result |
|---|---|
| Identify the hardware | MacPro1,1, Xeon 5150, 6 GB FB-DIMM, EFI32 |
| Confirm the TLS limitation | `curl https://api.anthropic.com` → `000` |
| Establish what is installed | Python 2.7.1 only; no Tailscale, brew, gcc, `/usr/local` |
| Map the disks | Single-member mirror + `Liferaft` clone + recovery |
| Determine account privileges | `ai-cockpit` is **not** admin, has no `sudo` |
| Audit the existing prototypes | Hardcoded tailnet IP; Custodian could never work |

The privilege finding drove much of the design: everything in the kit installs
and runs without an administrator password.

---

## Phase 1 — Portable TLS gateway · **DONE**

**Goal:** replace the unreachable hardcoded tailnet address with something a
new owner can actually run.

Design constraints, in priority order:

1. **Zero dependencies.** No pip, no venv, no `requirements.txt`. A new owner
   should get it running in under a minute on a fresh machine.
2. **Runs anywhere.** macOS, Linux, Windows — Python 3.7+ stdlib only.
3. **Keys never touch the vintage Mac.** They stay on the modern machine.
4. **Fails legibly.** Every error returns text the vintage client can display.

Delivered: `kit/gateway/aigw.py` (~430 lines, stdlib only).

- Providers: Anthropic, OpenAI, Gemini. Any one key is sufficient.
- Normalised request shape so the Python 2.7 clients stay simple.
- Client allowlist defaults to private ranges only (RFC1918 + CGNAT + loopback).
- Model defaults use `-latest` aliases, so retired model IDs do not strand the
  machine years from now.

**Two findings worth recording**, both discovered by testing rather than reasoning:

- *Stale model IDs.* `gemini-2.0-flash` now returns HTTP 404 "no longer
  available". Pinned versions are a time bomb on a machine nobody will maintain.
- *Thinking models truncate short replies.* Current Gemini models spend output
  tokens on internal reasoning before emitting text. At a 50-token budget the
  visible answer came back as `"GATE"` or empty. Measured for a one-line reply:

  | | total tokens | result |
  |---|---|---|
  | thinking on | 99 (88 thought) | correct, slower |
  | thinking off | 11 | correct, fast |

  Thinking is now off by default and opt-in per request.

---

## Phase 2 — Lion-side client kit · **DONE**

**Goal:** tools a non-expert can use, that degrade gracefully when the gateway
is absent.

Delivered to `/Users/Shared/ai-cockpit/` — chosen over a home directory so the
kit survives deleting the old account and works for any future user.

| Command | Purpose |
|---|---|
| `cockpit` | Full-screen interface: Oracle, Custodian, Retro-Coder, Status |
| `g5-config` | Settings; `g5-config test` sends a live prompt and reports plainly |
| `g5-doctor` | Health report in plain language; `--raw` works fully offline |
| `g5-assist` | English → shell command, screened and confirmed before running |
| `retro-port` | Back-port modern source so it builds here |

Four defects in the previous prototype were fixed; see `HANDOFF.md` §4.

The one worth restating: **the Custodian could never have worked.** It shelled
out to `sudo tail /var/log/system.log` from an account with no `sudo`, against
a file it had no permission to read. It was rebuilt on sources that need no
privileges — SMART status, ECC DIMM state, thermals, panic reports — which are
also precisely the components that fail on a machine of this age.

### Verification · **DONE**

Run on the machine, not assumed:

- All six modules compile under Python 2.7.1
- No-gateway path prints setup instructions instead of a traceback
- `g5-doctor --raw` works with no network at all
- **Live end-to-end:** the Mac Pro received `COCKPIT ONLINE` from a current
  Gemini model, through the gateway
- `g5-doctor` live produced an accurate report, correctly naming both drive
  models and noting the unreadable system log
- `g5-assist` safety screen: 12 commands tested, 9 destructive refused,
  3 safe allowed

---

## Phase 3 — Web cockpit · **DONE**

**Goal:** a modern interface for the new owner, combining everything.

Constraint that shapes it: **Next.js cannot run on this Mac.** No modern Node
runs on Lion, and Safari 6 cannot render a current React app. So the web cockpit
runs on the *new owner's* machine and drives the vintage one.

It implements the **same** `/health` and `/v1/chat/<provider>` contract as
`aigw.py`, making it a drop-in replacement: the Lion terminal clients can point
at either. Zero-dependency Python is the reliable floor; the web cockpit is the
comfortable front door.

Delivered: `kit/cockpit-web/`.

---

## Phase 4 — Linux starter pack · **NEW OWNER**

**Goal:** the path from "vintage curiosity" to "modern machine".

This is the phase with the highest payoff. Installing Linux does not work
*around* the TLS problem — it removes it. `claude`, `gemini`, and `aider` then
run natively with no gateway at all.

**Why this cannot be done for them:** installing an OS requires holding Option
at power-on and booting physical media. There is no remote equivalent.

Delivered instead, which is the useful half:

- `kit/linux/LINUX-STARTER-PACK.md` — install guide built around the real
  blocker. `firmware-abi = EFI32`: 64-bit CPU, 32-bit firmware, so standard
  modern USB installers will not boot. This is the single reason people give up
  on Linux on a 2006 Mac Pro. The guide routes around it via DVD boot (the
  machine has a working burner) rather than pretending USB will work.
- `kit/linux/bootstrap.sh` — idempotent post-install provisioning, `--dry-run`
  supported, validated on Debian/Ubuntu. Installs toolchains, Docker, the AI
  CLIs, `smartmontools` for real drive telemetry, sensible tuning for 6 GB and
  mechanical disks, and optionally `aigw.py` as a systemd service for *other*
  vintage machines.

The guide is deliberately honest about what a 2006 machine will and will not
do — including that local LLMs via Ollama run at roughly 1–3 tokens/second here
and are a novelty rather than a tool, and that the tower costs $20–30/month to
run continuously.

---

## Phase 5 — Privacy scrub · **BLOCKED — needs an admin password**

**Goal:** nothing of the previous owner leaves with the machine.

This is the one phase that is genuinely incomplete, and it is a hard permission
boundary rather than an oversight.

`/Users/administrator/` holds real personal data — Desktop (66 items),
Downloads (382), Documents (22), Trash (18), `.ssh/`, and project folders — all
mode `drwx------`. The automation account is not an administrator and has no
`sudo`, so that data cannot be read, archived, or deleted. That boundary
working correctly is a feature, not a bug.

Also outstanding: `ai-cockpit`'s `authorized_keys` still contains the previous
owner's public key, which would grant them SSH access *after* handover.

Delivered: `kit/scrub/scrub.sh` — previews everything, requires explicit
confirmation, offers to archive before deleting.

**This must be run from an administrator account before the machine ships.**

---

## Phase 6 — Dropped from the original plan, with reasons

Recorded so nothing looks accidentally forgotten.

| Original phase | Disposition |
|---|---|
| Break RAID, repartition `disk0` 850/150 | **Dropped.** Needs physical presence; an interrupted repartition leaves the machine unbootable the night before shipping |
| El Capitan via patched `boot.efi` | **Dropped.** Community EFI hack, requires USB boot. Linux serves the new owner far better |
| Tailscale exit node | **Dropped.** Ties the machine to the previous owner's private network — the opposite of a handover |
| Stripe webhook ingress → `192.168.1.127` | **Dropped and relocated.** Belongs on infrastructure that is staying. See §"xcelsior" below |
| Nginx load balancer / caching proxy | **Dropped.** Serves the old network only |
| Grafana + Prometheus scraping `xcelsior` | **Dropped.** Same reason |
| Lion `defaults write` tweaks | **Dropped.** Cosmetic, and imposes one person's preferences on the next owner |

The through-line: every dropped item existed to make this machine a component
of a network it is about to leave.

### xcelsior webhook testing

The webhook-ingress phase was the one dropped item with real ongoing value, so
it moves rather than disappears. Routing production webhooks through hardware
that ships tomorrow was never sound. Stripe CLI `listen --forward-to` tests the
same code path with no public ingress, no tunnel, and no dependency on this
machine. Tracked separately from the handover.

---

## Acceptance checklist

Before the machine leaves:

- [x] Machine boots; verified bootable, SMART clean on both disks
- [x] AI cockpit installed at `/Users/Shared/ai-cockpit/`
- [x] All modules compile on Python 2.7.1
- [x] Live end-to-end AI round trip proven from the Mac itself
- [x] Works gracefully with **no** gateway configured
- [x] `g5-doctor --raw` works with no network
- [x] Destructive-command guard verified independently
- [x] New owner's README on the machine
- [x] Linux starter pack + bootstrap on the machine
- [x] No hardcoded reference to the previous owner's network in the shipped kit
- [ ] **`kit/scrub/scrub.sh` run from an admin account** ← the remaining item
- [ ] Previous owner's `authorized_keys` removed (part of the scrub)

# Mac Pro 1,1 — Handover Record

**Prepared:** 16 August 2026
**Machine:** Mac Pro 1,1 (2006), hostname `Administrators-Mac-Pro.local`, LAN `192.168.1.124`
**Status at handover:** Healthy, bootable, verified. See §3.

This is the technical record of what the machine is, what was done to it, and
what was deliberately left alone. The document the *new owner* should read is
`kit/macos-lion/README.md`, which is installed on the machine itself at
`/Users/Shared/ai-cockpit/README.md`.

---

## 1. What this machine actually is

The two original plans (`g5-ai-integration-plan.md`, `macpro-omni-server-plan.md`)
were written from assumptions. Both were checked against the hardware. One was
substantially wrong, and it matters:

| Original plan said | Verified reality |
|---|---|
| "Power Mac G5", PowerPC 970 | **Mac Pro 1,1**, Intel Xeon 5150 |
| AltiVec vector intrinsics | **SSE/SSE2/SSSE3** — it is an Intel machine |
| OS X 10.5 Leopard, Python 2.5 | **OS X 10.7.5 Lion**, Python 2.7.1 |
| On the `xcelsior` Tailscale network | **Tailscale is not installed.** Plain LAN only |
| Gateway at Tailscale IP `100.64.0.6` | That address does not exist for a new owner |

The "G5" name is understandable — the Mac Pro 1,1 shares its aluminium
enclosure with the Power Mac G5 — but the internals are entirely different, and
every code-generation prompt targeting PowerPC would have produced code that
does not run here. This is corrected throughout the delivered kit.

### Verified specification

```
Model            MacPro1,1 (2006)
CPU              2 x Intel Xeon 5150 "Woodcrest" 2.66 GHz  (4 cores total)
Memory           6 GB DDR2 FB-DIMM, ECC enabled, all 6 slots "Status: OK"
Graphics         ATI Radeon X1900 XT, 512 MB
Disks            disk0  SAMSUNG HD103SI   1 TB  7200 rpm  SMART: Verified
                 disk1  ST31000333AS      1 TB  7200 rpm  SMART: Verified
Optical          OPTIARC DVD RW AD-7170A (reads and writes DVD)
Firmware         Boot ROM MP11.005C.B08,  firmware-abi = EFI32
OS               Mac OS X 10.7.5 Lion (build 11G63)
Python           2.7.1 (system)
Network          en0 wired, 192.168.1.124.  AirPort present but 802.11g
Not installed    Tailscale, Homebrew, gcc/Xcode, /usr/local
```

**`firmware-abi = EFI32` is the single most consequential fact** about this
machine. The CPU is 64-bit but the firmware is 32-bit EFI, which is why
standard modern Linux USB installers will not boot. Fully covered in
`kit/linux/LINUX-STARTER-PACK.md`.

---

## 2. The core constraint: this machine cannot do modern encryption

Lion ships OpenSSL 0.9.8za and curl 7.21.4. Modern endpoints require TLS 1.2+.
Measured on the machine:

```
$ curl -o /dev/null -w '%{http_code}' https://api.anthropic.com   ->  000
$ curl -o /dev/null -w '%{http_code}' https://api.openai.com      ->  000
```

`000` means no connection was established at all — not an HTTP error. Apple
ended Lion support in 2014, so this is permanent.

Everything in the delivered kit follows from this constraint. There are exactly
two honest ways to give this machine AI access:

1. **Proxy through a modern machine** (the gateway) — implemented, working.
2. **Replace the OS with Linux** — documented, requires physical media.

---

## 3. Verified state at handover

Checked immediately before writing this document:

| Check | Result |
|---|---|
| Boot volume | `/dev/disk2` mounted, 705 GB free of 931 GB |
| Blessed system | `/System/Library/CoreServices/boot.efi` present — bootable |
| RAID set `Macintosh RAID` | **Online — but see the warning below** |
| Recovery partition | present (`Boot OSX`, `disk0s3`) |
| `Liferaft` backup clone | present on `disk1`, 227 GB |
| `disk0` SMART | Verified |
| `disk1` SMART | Verified |
| Memory | 6 slots populated, all `Status: OK`, ECC enabled |
| Uptime at check | 1 day 22:54, load 0.45 |

**No disk-destructive operation was performed at any point.** All changes were
additive files under `/Users/Shared/`.

The machine currently has **three** independent ways to boot: the main system,
the `Liferaft` clone (hold Option at startup), and the recovery partition.

### The "RAID" provides no redundancy — important

The boot volume is an AppleRAID **mirror with exactly one member**:

```
Name:    Macintosh RAID      Type: Mirror      Status: Online
#  DevNode   Status    Size
0  disk0s2   Online    999860895744        <- one member, not two
```

A mirror needs two members to protect anything. This one has had its second
member removed (that drive is now `Liferaft`). It reports `Online` and works
perfectly, but **if `disk0` fails, the boot volume is gone.** The name invites
exactly the wrong assumption, so it is called out here.

The real safety net is the `Liferaft` clone on `disk1`, plus the recovery
partition.

### Partition layout as handed over

```
/dev/disk0                                    (Samsung HD103SI)
   1:  EFI                        209.7 MB
   2:  Apple_RAID                 999.9 GB    <- the live system, via disk2
   3:  Apple_Boot  "Boot OSX"     134.2 MB    <- recovery partition

/dev/disk1                                    (Seagate ST31000333AS)
   1:  EFI                        209.7 MB
   2:  Apple_HFS   "Liferaft"     999.9 GB    <- full clone of the Lion system

/dev/disk2      "Macintosh RAID"  999.9 GB    <- the mounted boot volume
```

The original plan's target layout (`disk0` split 850 GB Lion + 150 GB El
Capitan; `disk1` given wholly to Linux) was **not** created — see §5.

A new owner installing Linux does not need any of that done in advance. The
Debian installer repartitions `disk1` itself, attended, with its own
safeguards. That is a far safer way to do it than pre-carving the disks now.

### Disk health assessment

Both drives pass SMART and are the correct kind of "fine for now":

- `disk0` — Samsung HD103SI, ~2009-era 1 TB 5400/7200-class drive
- `disk1` — Seagate **ST31000333AS**, firmware LC15. This is a Barracuda
  7200.11, the family notorious for a firmware bug causing sudden
  "drive disappears / 0 LBA" lockups. LC15 is not the specific affected
  revision (SD15 was), but the family history is worth the new owner knowing.

Both are roughly 15+ years old and past typical service life. SMART "Verified"
on Lion is only a pass/fail summary — it does not expose reallocated-sector
counts or power-on hours. Lion has no `smartctl`. **The Linux starter pack
installs `smartmontools`, which does expose those**, and that is the fastest
route to a real answer on remaining drive life.

Bottom line for the new owner: **do not keep the only copy of anything here.**

---

## 4. What was built and installed

Installed on the machine at `/Users/Shared/ai-cockpit/` — deliberately in
`/Users/Shared` so it survives account deletion and works for any future user.

| Component | Purpose |
|---|---|
| `aigw.py` | Zero-dependency Python 3 TLS gateway. Runs on the *new owner's* modern machine |
| `g5ai.py` | Shared client library, Python 2.7 stdlib only |
| `cockpit.py` | Full-screen terminal interface (Oracle / Custodian / Retro-Coder / Status) |
| `g5_config.py` | `g5-config` — settings and connection testing |
| `g5_doctor.py` | `g5-doctor` — hardware health, explained in plain language |
| `g5_assist.py` | `g5-assist` — plain English to a shell command, with a safety screen |
| `retro_port.py` | `retro-port` — back-port modern source so it builds here |
| `install.sh` | Idempotent installer, requires no admin rights |
| `README.md` | The new owner's guide |

### Verification performed

Not assumed — actually run on the machine:

- All six Python files compile under Lion's Python 2.7.1 (`py_compile`, no errors)
- `install.sh` completes and puts commands on `PATH`
- `g5-config show` with no gateway → prints setup instructions, does not crash
- `g5-doctor --raw` → works fully offline, no network
- Live end-to-end: gateway on a modern box → Mac Pro received **`COCKPIT ONLINE`**
  from a current Gemini model. *A machine that cannot complete a TLS handshake
  held a conversation with a 2026 language model.*
- `g5-doctor` live → produced an accurate health report that correctly
  identified both drive models, the RAID volume, memory layout, and the
  unreadable system log
- `g5-assist` safety screen tested independently against 12 commands:
  all 9 destructive ones refused, all 3 safe ones allowed

### Bugs found and fixed from the previous prototype

1. **Hardcoded gateway address.** The old `cockpit.py` hardcoded
   `http://100.64.0.6:8081`, a private Tailscale IP. For a new owner this is
   unreachable and un-fixable without editing source. Now configuration-driven
   with no address compiled in.
2. **Custodian could never work.** It ran `sudo tail /var/log/system.log`, but
   that file is `root:admin 0640` and the `ai-cockpit` account is neither root
   nor admin, and has no sudo. It silently produced a permission error instead
   of diagnostics. Rebuilt around sources readable without privileges — SMART
   status, ECC DIMM state, thermals, panic reports — which are also the things
   that actually fail on this model.
3. **Retro-Coder was never implemented** — the menu entry printed "not yet
   implemented". Now working, and corrected from PowerPC/AltiVec to Intel/SSE.
4. **Stale model IDs.** `gemini-1.5-pro` and `claude-3-5-sonnet-20240620` are
   retired; the API returns 404. Defaults now use the `-latest` alias so the
   machine keeps working as models change without anyone editing code.
5. **Empty replies from modern models.** Current Gemini models spend output
   tokens on internal reasoning before emitting text, so the old 800-token
   budget returned truncated or empty answers. Measured: thinking on = 99
   tokens for a one-line reply; thinking off = 11 tokens, same answer. The
   gateway now disables thinking by default.
6. **Serial number leakage.** Diagnostics included the hardware serial and UUID
   and sent them to a third-party API. Now redacted before transmission.

---

## 5. What was deliberately NOT done

Stated plainly so nothing looks accidentally missing.

### The omni-server repartition (original plan Phases 1–3)

The `macpro-omni-server-plan.md` called for breaking the RAID, repartitioning
`disk0` into 850 GB Lion + 150 GB El Capitan, patching the El Capitan installer
to bypass the 32-bit EFI lock, and installing Linux on `disk1`.

**Not done, for three reasons:**

1. **Physically impossible remotely.** It requires holding Option at power-on
   and booting from USB/DVD. There is no remote equivalent.
2. **Unacceptable risk against the deadline.** An interrupted repartition
   leaves the machine unbootable, and it ships tomorrow.
3. **It solves the wrong problem.** Those phases existed to make the machine a
   node on the *previous owner's* network — Tailscale exit node, Stripe webhook
   ingress to `192.168.1.127`, Grafana scraping `xcelsior` hosts. None of that
   should follow the machine to a new owner. It is the opposite of a clean
   handover.

Phase 1 was already partially completed before this work began: the mirror was
broken and Lion cloned to `Liferaft` on `disk1`. That clone was left in place —
it is a genuine safety net for the new owner.

The Linux half of the goal is fully served by `kit/linux/`, which is the part a
new owner actually benefits from.

### The `administrator` account's personal data

**Not removed — and I could not remove it.** See §6.

---

## 6. Privacy status — NO SCRUB. THE RECIPIENT OWNS THIS DATA.

**Superseded.** This section originally called for wiping the `administrator`
account before handover. That was wrong for this handover and the instruction
is withdrawn.

The machine is going to the person who owns that account. Their files are not
"previous owner data to be removed" — they are the recipient's own files, and
`Liferaft` is their backup. **Do not run `kit/scrub/scrub.sh`.**

Keep as-is:

- `/Users/administrator/` — all of it
- `/Volumes/Liferaft` — their system backup (until the Linux install consumes
  that disk, which is a decision they make in the runbook)
- Shell history, application settings, everything else

The only genuinely optional item is the operator SSH key in
`/Users/ai-cockpit/.ssh/authorized_keys`. It grants remote access to whoever
set up the automation. Keep it for continued remote help, or
`rm` it for full independence. Reversible either way.

`scrub.sh` is retained in the kit for a future handover to a *different*
person. It previews by default and requires typing `YES`, so it cannot fire by
accident — but it should not be run now.

### For reference, what the account contains

(Recorded during the audit, before the recipient was identified. Left here
because it documents what is being *preserved*.)

```
Desktop      66 entries
Downloads   382 entries
Documents    22 entries
.Trash       18 entries
.ssh/        present
CompudataLINK, Sites, projects, Applications
```

All are mode `drwx------`, owned by `administrator`. The automation account
(`ai-cockpit`) is not an administrator and has no `sudo`, so it could not read
them — correctly, since that boundary is what stops an automation account from
touching another user's private files. **That data stays exactly where it is.**

---

## 7. Day one for the new owner

1. Power on. Lion boots normally.
2. Read `/Users/Shared/ai-cockpit/README.md`.
3. To get AI working, run the gateway on a modern computer and point the Mac at
   it — about five minutes, covered step by step in that README.
4. Optionally install Linux on the second drive using
   `/Users/Shared/ai-cockpit/docs/LINUX-STARTER-PACK.md`.

Nothing in the kit requires an internet connection *from the Mac itself* to set
up, and nothing requires an administrator password.

---

## 8. Connecting to this machine from a modern computer

Modern OpenSSH refuses Lion's older host-key and signature algorithms by
default. This is not a fault on either side. Use:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    user@192.168.1.124
```

Without those flags you get `no matching host key type found. Their offer:
ssh-rsa,ssh-dss`, which looks like a failure but is only a policy mismatch.

---

## 9. Files in this handover

```
g5-handoff/
├── HANDOFF.md                      this document
├── IMPLEMENTATION-PLAN.md          the phased build plan
├── README.md                       index
├── g5-ai-integration-plan.md       original plan, unmodified, for the record
├── macpro-omni-server-plan.md      original plan, unmodified, for the record
└── kit/
    ├── gateway/aigw.py             the TLS gateway
    ├── macos-lion/                 everything installed on the machine
    ├── linux/                      starter pack: install guide + bootstrap.sh
    ├── cockpit-web/                Next.js web cockpit (runs on a modern machine)
    └── scrub/scrub.sh              privacy scrub — RUN BEFORE SHIPPING
```

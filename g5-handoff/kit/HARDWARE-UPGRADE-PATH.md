# Hardware Upgrade Path — going newer than El Capitan

El Capitan (10.11) is the newest macOS this machine can run **as currently
configured**. That ceiling is set by the CPUs, not by the firmware, and it can
be lifted — but only with a hardware change.

This is a separate project. Nothing here is required for the machine to work.

---

## Why El Capitan is the wall

Verified on this machine:

```
$ sysctl -n machdep.cpu.features
... MMX FXSR SSE SSE2 SSE3 SSSE3 CX16 ...
  SSE4.1: NO    SSE4.2: NO    POPCNT: NO    AVX: NO
```

**macOS Sierra (10.12) and every release after it require SSE4.1.** The Xeon
5150 "Woodcrest" (2006, 65 nm, Core micro-architecture) predates that
instruction set.

This is a kernel-level instruction requirement, not a compatibility check that
can be patched out. Community patchers such as dosdude1's work around Apple's
*model* restrictions and the 32-bit EFI; none of them can synthesise a CPU
instruction that the silicon does not implement. That is why the community
ceiling for a stock MacPro1,1 is El Capitan.

## What lifts it: 45 nm Xeons

The Xeon **5400 series ("Harpertown", 45 nm, Penryn-based)** does have SSE4.1.
Fitting those makes Sierra and later technically possible.

Two things are required together:

### 1. Firmware flash: MacPro1,1 → MacPro2,1

The 1,1 firmware does not recognise the 45 nm parts. Flashing the machine to
identify as a **MacPro2,1** adds the microcode and support needed. This is a
long-standing, well-documented community procedure.

**Do this first, and do it while the machine still boots.** A firmware flash is
the single riskiest thing you can do to a Mac — a failure mid-write can leave it
unable to power on. Have the machine on stable power, and do not attempt it on a
machine you cannot afford to lose.

### 2. CPUs: matched pair, LGA771, 1333 MHz FSB

This machine has a 1333 MHz front-side bus, so choose parts that match it:

| CPU | Cores | Clock | Notes |
|---|---|---|---|
| **X5450** | 4 | 3.00 GHz | common, good value |
| **X5460** | 4 | 3.16 GHz | popular sweet spot |
| **X5470** | 4 | 3.33 GHz | fastest 1333 MHz FSB option |
| E5450 | 4 | 3.00 GHz | lower TDP alternative |

Buy a **matched pair** — same model, ideally same stepping. Eight cores total
replaces the current four.

These are cheap secondhand now; they were server parts produced in volume.

### Practical notes

- The existing heatsinks fit. **Replace the thermal paste** — the original is
  nineteen years old and will be chalk.
- The CPU trays on this model require care to remove. Work slowly; the retention
  hardware is not forgiving.
- Expect the fans to behave differently afterwards. The 2,1 firmware drives them
  from different thermal profiles.

## What you get, and the second wall

With 2,1 firmware and Harpertown CPUs:

| OS | Feasible? | Blocker |
|---|---|---|
| Sierra 10.12 | yes | — |
| **High Sierra 10.13** | yes | best realistic target |
| Mojave 10.14 | **only with a GPU swap** | requires a Metal-capable GPU |
| Catalina 10.15+ | no | drops 32-bit support and hardware this old entirely |

**High Sierra is the sensible destination.** Mojave's patcher requires a
Metal-capable graphics card, which your Radeon X1900 XT is not — so Mojave means
a third purchase on top of the CPUs and the flash.

Use **dosdude1's High Sierra Patcher** for the install; it handles both the
unsupported-model check and the 32-bit EFI boot.

## Graphics — worth considering on its own

Independent of any CPU work, the X1900 XT has no driver past Lion. Apple deleted
the R500-series kexts, which is why El Capitan will run here without graphics
acceleration.

A supported card fixes that and is far less risky than a firmware flash:

- **Radeon HD 5770 / 5870 (Mac Edition)** — the classic choice
- **NVIDIA GT 120 / GTX 680** (Mac-flashed)

Note: with 32-bit EFI you need a **Mac-flashed** card to see boot screens. A PC
card generally works once the OS loads, but the Option-key picker stays dark —
which matters on a machine where choosing the boot volume is routine.

## Memory

Takes DDR2 FB-DIMMs in matched pairs, up to 32 GB. Currently 6 GB.

FB-DIMMs run hot and are the most common failure on this model. If you add
memory: keep the heatsinks on, keep the dust out, and watch the ECC counters
(`macpro-doctor` on Linux reports them, once `i5000_edac` is loaded).

## Honest cost/benefit

| Upgrade | Rough cost | What it buys |
|---|---|---|
| Nothing | £0 | Lion + El Capitan + Linux. Already achieved. |
| GPU only | low | graphics acceleration in El Capitan, boot screens |
| CPUs + flash | low, plus real risk | High Sierra becomes possible |
| CPUs + flash + GPU | moderate | Mojave, the practical maximum |

For most purposes **none of this is needed**. Linux on the second drive already
gives current security updates, a modern browser, and native AI tooling — on the
existing hardware, with no risk. The upgrades above matter if you specifically
want a *newer macOS*, which is a different goal.

## Before you start any of it

Back up first. The firmware flash in particular has a non-trivial chance of
leaving you with a machine that will not power on, and there is no recovery from
that without specialist equipment.

# Partition & Triple-Boot Runbook — Mac Pro 1,1

**Target layout requested:**

```
disk0 (Samsung HD103SI, 1 TB)   150 GB  El Capitan
                                 ~850 GB  Lion  (same environment as today)
disk1 (Seagate ST31000333AS)    1 TB     Linux
```

This runbook is written to be followed in order. **The ordering is the part
that matters** — get it wrong and you destroy your only copy of Lion. Read §1
before touching anything.

---

## 0. Two blockers found on this machine

Both were verified on the hardware, not assumed.

### Blocker A — `disk0` cannot be repartitioned from the running system

The boot volume is an AppleRAID mirror set (`disk2`), whose single member is
`disk0s2`, typed `Apple_RAID`. Attempting to resize it:

```
$ diskutil resizeVolume disk2 limits
Error obtaining resizing information

$ diskutil resizeVolume disk0s2 limits
Volume format does not support resizing
```

AppleRAID volumes do not support resizing, and you cannot restructure the disk
you are booted from. **You must boot from something else to do this work.**

Fortunately you already have the something else: the `Liferaft` clone on
`disk1`. That is exactly what it is for.

### Blocker B — this CPU is x86-64-**v1**

```
$ sysctl -n machdep.cpu.features
... SSE SSE2 SSE3 SSSE3 ...        <- and nothing beyond
  SSE4.1: NO    SSE4.2: NO    POPCNT: NO    AVX: NO
```

The Xeon 5150 (Woodcrest, 2006) predates SSE4.2 and POPCNT, which are the
defining requirements of the **x86-64-v2** baseline. Ubuntu's own documentation
describes v2 as covering processors "from 2009 onward". This machine is 2006.

**Therefore: Ubuntu 26.04 is not a safe choice here.**

| Concern | Detail |
|---|---|
| CPU baseline | x86-64-v1 only. Distros moving to a v2 baseline will not boot |
| RAM | Ubuntu 26.04 raised the desktop minimum to 6 GB. This machine has exactly 6 GB — no headroom |
| Installer | Ubuntu's installer assumes 64-bit UEFI; this machine is `EFI32` |
| Graphics | Radeon X1900 (2006) against a modern GNOME desktop |

**Recommendation: install Debian 13 instead.** It still targets baseline
`amd64` (v1), is far lighter on this hardware, and its installer can place a
32-bit EFI bootloader. If you specifically want Ubuntu, use **Xubuntu 24.04
LTS** rather than 26.04 — but verify it boots before committing the disk.

If you want to try Ubuntu 26.04 anyway, do it **last**, after Lion and El
Capitan are restored and verified, so a failure costs you nothing.

---

## 1. Ordering — read this before starting

`Liferaft` (your only backup of Lion) is on `disk1`. `disk1` is also where Linux
is going. So there is exactly one safe order:

```
  1. Verify Liferaft actually boots           <- do not skip
  2. Boot FROM Liferaft
  3. Rebuild disk0:  150 GB + 850 GB
  4. Restore Lion from Liferaft -> disk0 850 GB partition
  5. Boot the restored Lion and verify it works
  6. Install El Capitan -> disk0 150 GB partition
  7. ONLY NOW: wipe disk1 and install Linux
```

**Do not wipe `disk1` before step 5 succeeds.** Between steps 3 and 5, Liferaft
is your only copy of the system.

If you have an external drive, clone Liferaft to it first. That removes the
single point of failure entirely, and is the difference between a bad evening
and a lost machine.

---

## 2. Verify the safety net (do not skip)

Restart holding **Option**. You should see `Liferaft` as a bootable choice.
Boot it. Confirm it reaches the desktop and looks like your system.

If it does not boot, **stop.** Everything below assumes it does.

---

## 3. Rebuild disk0 (booted from Liferaft)

You are now running from `disk1`, so `disk0` is free to restructure.

Confirm which disk is which — identifiers can move between boots:

```bash
diskutil list
```

Expect `disk0` = SAMSUNG HD103SI, `disk1` = ST31000333AS (now your boot volume).
**Verify by model name, not by number.**

Dissolve the RAID set on disk0:

```bash
diskutil appleRAID list
diskutil appleRAID delete <the-RAID-set-UUID>
```

Then partition disk0 — two HFS+ volumes, GUID partition scheme:

```bash
diskutil partitionDisk disk0 GPT JHFS+ "El Capitan" 150G JHFS+ "Lion" R
```

`R` means "the remainder", giving Lion roughly 850 GB. Verify:

```bash
diskutil list disk0
```

> Everything on `disk0` is now gone. This is the destructive step. It is safe
> only because Liferaft holds a complete copy — which you verified in §2.

---

## 4. Restore Lion to the 850 GB partition

Still booted from Liferaft. Use Disk Utility (easier to get right than the CLI):

1. Open **Disk Utility**
2. Select the **Lion** partition on disk0 (the destination)
3. Go to the **Restore** tab
4. Drag **Liferaft** to *Source*, the **Lion** partition to *Destination*
5. Click **Restore**

Roughly 227 GB will copy. Expect 1–3 hours on these mechanical drives.

Equivalent CLI, if you prefer:

```bash
sudo asr restore --source /Volumes/Liferaft --target /Volumes/Lion --erase
```

Then bless it so it is bootable:

```bash
sudo bless --folder /Volumes/Lion/System/Library/CoreServices --bootefi
```

---

## 5. Verify the restored Lion — the checkpoint

Restart holding **Option** and boot the **Lion** partition on `disk0`.

Confirm all of:

- [ ] It reaches the desktop
- [ ] Your files are present
- [ ] Networking works
- [ ] `/Users/Shared/ai-cockpit/bin/g5-config show` runs

**Only once every box is ticked is `disk1` expendable.** Until then, Liferaft
stays exactly where it is.

---

## 6. Install El Capitan to the 150 GB partition

El Capitan (10.11) does not officially support the Mac Pro 1,1 — the machine's
32-bit EFI is below its minimum. It requires a community-patched installer
(the "MacPostFactor" / "Pikify" approach referenced in the original plan).

**You have the patched installer**, so this step is viable. Procedure:

1. Put the patched installer on a USB drive from a modern Mac.
2. Boot the Mac Pro holding **Option**.
3. Select the installer.
4. Install to the **El Capitan** partition — the 150 GB one created in §3.

**Do not let it touch the Lion partition.** The installer will happily offer it.
Confirm the destination name and size on the selection screen before continuing.

Two cautions worth knowing before you start:

- The patch works by substituting a `boot.efi` that the stock installer refuses
  to use. It is unofficial, unsupported, and can be broken by any later system
  update — do not apply macOS updates to that partition casually.
- El Capitan left security support in 2018. Its Safari cannot reach most of the
  modern web either. It is more capable than Lion, but it is not a solution to
  the TLS problem — Linux on `disk1` is. Treat El Capitan as the bridge for
  period software that needs something newer than Lion, not as the daily driver.

---

## 7. Install Linux to disk1

Only after §5 passed.

Follow [`linux/LINUX-STARTER-PACK.md`](linux/LINUX-STARTER-PACK.md), which
covers the `EFI32` boot problem in detail. In short:

- Burn the installer to a **DVD**, not USB. This machine has a working burner,
  and DVD boot uses the legacy BIOS path that sidesteps the 32-bit EFI problem.
- Boot holding **Option**, choose the disc (it may be labelled "Windows" — that
  is the generic non-Apple icon and is expected).
- At partitioning, select **`disk1`** — verify by model (ST31000333AS) and size.
- Install GRUB to that same disk. **Not** to `disk0`.

Then run the provisioning script:

```bash
./bootstrap.sh --dry-run     # preview
./bootstrap.sh               # do it
```

---

## 8. Result

```
Hold Option at startup to choose:

  Lion         disk0, ~850 GB   your existing environment, AI Cockpit installed
  El Capitan   disk0, 150 GB    if you completed §6
  Linux        disk1, 1 TB      modern OS, modern TLS, native AI CLIs
```

Optionally install **rEFInd** on the Lion side for a graphical boot menu on
every startup instead of holding Option: <https://www.rodsbooks.com/refind/>

---

## 9. If something goes wrong

**Nothing boots after §3.** Boot from the `Boot OSX` recovery partition, or
hold Option and pick Liferaft. Liferaft is untouched until §7.

**The restore in §4 fails partway.** Liferaft is still intact — it was the
source, not the destination. Repartition disk0 and try again.

**Linux installed but the Mac boots straight to macOS.** Normal. Hold Option at
startup; the Linux disk appears as "Windows". Install rEFInd for a proper menu.

**Ubuntu 26.04 will not boot / halts early.** Expected on this CPU — see
Blocker B. Use Debian 13.

---

## What was NOT done for you, and why

None of this was executed remotely. Every step above requires either holding a
key at power-on or booting from different media — there is no remote
equivalent, and an interrupted repartition leaves an unbootable machine.

The machine is currently in a **known-good, fully bootable state** with three
independent boot paths (main system, Liferaft, recovery). That is the right
state to hand over in, and the right state to start this runbook from.

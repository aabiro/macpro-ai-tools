# Boot Steps — Mac Pro 1,1

Every boot transition in `PARTITION-RUNBOOK.md`, in order, with exactly what you
should see at each one.

The disk work is the dangerous part; **the boots are the fiddly part**. On a
machine this old the Startup Manager is timing-sensitive and unhelpfully quiet
when something is wrong. This document exists so you never have to guess whether
it is broken or just slow.

---

## 0. Before you touch the power button

### A wired USB keyboard is effectively mandatory

**This is the single most common failure.** Bluetooth keyboards are not powered
up early enough in this machine's boot to register the Option key. You will hold
Option, nothing will happen, and you will conclude the machine is broken.

- Use a **wired USB keyboard**
- Plug it **directly into the Mac**, not into a hub, monitor, or the keyboard's
  own passthrough port
- Front or rear ports both work

If you only have Bluetooth, see §9 for setting the startup disk from software
instead.

### Have these ready

| | |
|---|---|
| Wired USB keyboard | required, see above |
| Wired Ethernet cable | the 2006 AirPort card is unreliable under Linux |
| Debian USB stick | already written and verified |
| El Capitan USB | your community-patched installer, if doing that step |
| Time | do not start step 3 of the runbook an hour before you need the machine |

---

## 1. Getting into the Startup Manager

This is the boot picker. You will use it for every step below.

1. Fully shut down (Apple menu → Shut Down). Not restart, for the first time —
   a cold start makes the timing easier to judge.
2. Press the power button.
3. **Immediately** press and hold **Option** (⌥, also labelled Alt).
   Start holding it before you hear the chime, not after.
4. Keep holding until the screen shows a dark background with drive icons.
   That can take **15–30 seconds**, and longer if a USB stick is plugged in.
   The screen may stay black or grey for a while first. This is normal.
5. Release Option when icons appear.

Navigate with **← →** arrow keys. Press **Return** to boot the highlighted one.

> **If no icons ever appear** and you land in the normal system: the Option key
> was not registered. Almost always the keyboard. Re-read §0, then try again
> holding Option *before* pressing power and keeping it held.

---

## 2. Reading the picker

You will see some combination of:

| Icon / label | What it actually is |
|---|---|
| `Macintosh RAID` | your current Lion system on `disk0` |
| `Liferaft` | the clone on `disk1` |
| `Recovery HD` | the small recovery partition |
| `Windows` | **any non-Apple bootable disc or drive.** This is the generic icon. Your Debian DVD or USB appears here — the label is wrong and expected |
| `EFI Boot` | a USB with an EFI bootloader — the Debian Mac image may appear this way |

**Do not be alarmed by "Windows".** There is no Windows on this machine. It is
the label Apple gives to anything booting the legacy/BIOS path.

Names change as you work through the runbook. After you repartition, `Macintosh
RAID` disappears and `Lion` and `El Capitan` appear. Always read the label
before pressing Return.

---

## 3. Boot 1 — verify `Liferaft` actually boots

**Do this before any disk work. Everything downstream assumes it.**
Nothing here is destructive. You are only proving the safety net works.

Budget 20–30 minutes.

### 3a. Before you shut down

1. **Save your work.** `administrator` is logged in at the console with
   applications open. Save and quit anything with unsaved documents —
   Preview, Safari, Terminal, TextEdit.
2. **Note that remote access drops.** Anyone helping over SSH loses the
   connection at shutdown and reconnects once the machine is up again.
3. **Plug in a wired USB keyboard**, directly into the Mac. See §0. This is the
   step people skip and then spend an hour on.
4. **Unplug USB sticks** you are not booting from. They slow the picker and add
   confusing entries.

### 3b. Shut down properly

**Apple menu () → Shut Down…** → confirm.

Use Shut Down, not Restart, for this first attempt — a cold start makes the
Option timing much easier to judge. Wait for the fans to stop completely.

### 3c. Boot into the picker

1. Press the power button
2. **Immediately** press and hold **Option (⌥)** — before the chime, not after
3. Hold it. The screen may be black or grey for **15–30 seconds**. Normal.
4. Release when drive icons appear

### 3d. Choose `Liferaft`

You should see roughly:

```
   [Macintosh RAID]      [Liferaft]      [Recovery HD]
```

Use **← →** to highlight **`Liferaft`**, press **Return**.

If `Liferaft` is not there, **stop** and see §3g.

### 3e. Wait

First boot from a clone is slow. A grey screen with a spinning gear for
**2–5 minutes** is expected. Do not power off. If nothing at all has happened
after 10 minutes, power off and see §3g.

Log in as you normally would.

### 3f. Confirm you are actually on `Liferaft` — do not skip

**`Liferaft` is a byte-for-byte clone. It will look exactly like your normal
system — same wallpaper, same files, same everything.** Looking at the desktop
tells you nothing. You must check.

Open **Terminal** (Applications → Utilities → Terminal) and run:

```bash
df -h /
```

| Output shows | Meaning |
|---|---|
| `/dev/disk1s2` | ✅ **on `Liferaft`** — the clone boots. This is what you want |
| `/dev/disk2` | ❌ you booted the normal system. The picker selection did not take — retry §3c |

Confirm the rest:

```bash
diskutil list          # responds, shows both disks
ls ~/Documents         # your files are here
ping -c3 192.168.1.1   # networking works
```

**Two things that are normal on `Liferaft` and are NOT faults:**

- `g5-config` / `cockpit` / `g5-doctor` are **missing**. The clone was made
  before the AI kit was installed. Expected. They are on the main system.
- The volume mounted at `/Volumes/Macintosh RAID` is now your *other* system.
  Do not modify it here.

### 3g. If `Liferaft` will not boot — STOP

**Do not start the runbook.** Without a working clone there is no safety net,
and runbook §3 erases `disk0`.

| Symptom | Do this |
|---|---|
| No icons ever appear | Keyboard. Wired USB, directly into the Mac, hold Option *before* pressing power |
| Icons appear, no `Liferaft` | Reset NVRAM (§9) and retry. If still absent, the clone is not blessed — see below |
| Selected it, grey screen forever | Power off. Boot the normal system. The clone is damaged; re-clone before proceeding |
| Folder with `?` | No bootable system found. Boot normally, then re-bless (below) |

Re-bless the clone from the **normal** system:

```bash
sudo bless --folder "/Volumes/Liferaft/System/Library/CoreServices" --bootefi
```

Then retry §3c. If it still will not boot, re-make the clone with Disk Utility
(Restore tab, source = your system, destination = `Liferaft`) before continuing.

### 3h. Return to normal

Boot 1 is only a verification. When satisfied:

**Apple menu () → Restart**, hold **Option**, choose **`Macintosh RAID`**.

Confirm you are back:

```bash
df -h /                    # expect /dev/disk2
g5-config show             # the AI kit is here again
```

✅ **Boot 1 passes when `Liferaft` booted and `df -h /` showed `/dev/disk1s2`.**
You are cleared for Boot 2.

---

## 4. Boot 2 — run the disk work *from* `Liferaft`

You cannot repartition the disk you are booted from, and `disk0` carries an
AppleRAID set that refuses to resize (verified — see the runbook's Blocker A).
So you work on `disk0` while running from `disk1`.

1. Startup Manager (§1)
2. Select **`Liferaft`** → Return
3. Once at the desktop, open **Terminal** and confirm where you are:

```bash
diskutil list
df -h /
```

**Check before proceeding:** `/` must be on `disk1`, and the Samsung HD103SI
must be `disk0`.

> **Identifiers move.** `disk0` and `disk1` are assigned in detection order and
> can swap between boots, especially with a USB stick attached. **Always verify
> by model name** — `SAMSUNG HD103SI` vs `ST31000333AS` — never by number alone.
> This is the mistake that erases the wrong drive.

Now run runbook §3 and §4 (dissolve the RAID, partition, restore Lion).

Leave the machine alone during the restore. It takes 1–3 hours on these
mechanical drives. Do not let it sleep — set Energy Saver to never sleep first.

---

## 5. Boot 3 — verify the restored Lion (the checkpoint)

**This is the gate. `Liferaft` is expendable only after this passes.**

1. Startup Manager (§1)
2. Select **`Lion`** — the newly restored volume on `disk0`, roughly 850 GB
3. Return

**Confirm all of:**

- [ ] Reaches the desktop
- [ ] Your files are present
- [ ] Networking works (load a local page, or `ping -c3 192.168.1.1`)
- [ ] `/Users/Shared/ai-cockpit/bin/g5-config show` runs

**Until every box is ticked, do not touch `disk1`.** If something is wrong, boot
`Liferaft` again and redo the restore — the clone is still intact because it was
the source, not the destination.

---

## 6. Boot 4 — El Capitan installer (optional)

Only if you are doing the 150 GB El Capitan partition.

1. Plug in the patched installer USB
2. Startup Manager (§1) — **wait longer**, USB scanning adds 10–20 seconds
3. The installer appears as **`EFI Boot`**, `Install OS X El Capitan`, or an
   orange/grey external-drive icon
4. Select it → Return

**At the destination screen, select `El Capitan` — the 150 GB volume.**

> The installer will happily offer the Lion partition. Read the volume name and
> the size before clicking. This is the second-most-likely way to lose Lion.

If the USB never appears: the patched installer was not built correctly for
32-bit EFI. That is a problem with the USB, not the Mac. Rebuild it.

---

## 7. Boot 5 — Debian installer

1. Plug the Debian USB into a **rear** port directly on the Mac
2. Startup Manager (§1) — again, wait for USB scanning
3. Look for **`EFI Boot`** or **`Windows`**. Either can be the Debian stick —
   the image carries a 32-bit EFI bootloader, so it usually shows as `EFI Boot`
4. Select it → Return
5. At the Debian menu choose **`Install`** (the plain text installer is more
   reliable here than the graphical one)

**If it does not appear after 60 seconds:**

- Try a different USB port (rear ports are more reliable at boot on this model)
- Reset NVRAM (§9) and retry
- Fall back to burning the DVD — the optical drive uses the legacy boot path
  and is the most reliable route on this machine:
  ```bash
  /Users/Shared/ai-cockpit/linux/burn-installer.sh
  ```

### At the partitioner — the highest-stakes screen in this document

Select the **Seagate ST31000333AS**. That is the `Liferaft` disk, now expendable
because §5 passed.

**Do NOT select the SAMSUNG HD103SI.** That is Lion and El Capitan.

Linux names disks `sda`/`sdb`, not `disk0`/`disk1`, and the ordering has no
relationship to macOS's. **Match on the model string shown by the installer.**
If the installer shows only sizes and both are 1 TB, back out and identify them
by model first — do not guess.

Install GRUB to that **same** disk. Not to the Samsung.

---

## 8. Boot 6 — into installed Linux, and everyday use

After installation the Mac still boots macOS by default. That is normal — it is
not a failed install.

To boot Linux: **Startup Manager → the entry labelled `Windows` → Return.**

To stop holding Option every time, either:

- **Set a default:** boot macOS → System Preferences → Startup Disk → choose one.
  Note macOS often cannot see the Linux volume here; use rEFInd instead if so.
- **Install rEFInd** on the Lion side for a proper graphical boot menu on every
  start: <https://www.rodsbooks.com/refind/>

First thing after first Linux boot:

```bash
./bootstrap.sh --dry-run     # preview
./bootstrap.sh               # provision
```

---

## 9. Key combinations and recovery

Hold each immediately after the power button, with a **wired** keyboard.

| Keys | Effect | Use when |
|---|---|---|
| **Option (⌥)** | Startup Manager | every step above |
| **⌘ + Option + P + R** | Reset NVRAM/PRAM — hold through two chimes | picker misbehaving, USB not detected, wrong default disk |
| **Shift** | Safe boot | system boots but misbehaves |
| **⌘ + V** | Verbose boot — shows text instead of the Apple logo | diagnosing a hang; tells you *where* it stops |
| **⌘ + S** | Single-user mode | filesystem repair |
| **C** | Boot from CD/DVD directly | skipping the picker for a burned disc |
| **T** | Target disk mode | pulling files off via FireWire |
| **Mouse button held** | Eject a stuck disc | disc trapped in the drive |

**SMC reset** (won't power on at all): shut down, unplug the power cord, wait
15 seconds, plug back in, wait 5 seconds, press power.

---

## 10. If nothing boots at all

You have three independent paths, and they fail independently. In order of
preference:

1. **Startup Manager → `Recovery HD`** — Disk Utility to repair the volume
2. **Startup Manager → `Liferaft`** — intact until runbook §7 consumes it
3. **Verbose boot (⌘V)** — read where it stops; a specific failing line is far
   more actionable than a grey screen

If the picker itself never appears with a confirmed wired keyboard, reset NVRAM
(§9), then SMC. Both are safe and non-destructive.

**A grey screen with a folder-with-question-mark** means no bootable system was
found — usually the blessed volume was lost, not the data. Boot `Recovery HD` or
`Liferaft` and re-bless:

```bash
sudo bless --folder /Volumes/Lion/System/Library/CoreServices --bootefi
```

---

## Sequence at a glance

```
  Boot 1   Liferaft          verify the safety net           <- do not skip
  Boot 2   Liferaft          dissolve RAID, partition disk0,
                             restore Lion                    <- destructive
  Boot 3   Lion (disk0)      VERIFY                          <- the gate
  Boot 4   El Capitan USB    install to the 150 GB volume    <- optional
  Boot 5   Debian USB        install to ST31000333AS         <- erases Liferaft
  Boot 6   Linux             bootstrap.sh
```

Boots 1, 3 are checkpoints — nothing destructive happens on them, and each one
you skip is a failure you discover later, when the recovery options are fewer.

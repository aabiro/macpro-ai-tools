# Linux boot & display on this Mac Pro — the one real gotcha

Debian 13 (trixie) runs well on this machine, but it **will not display anything**
past about three seconds into boot unless the kernel is told to leave the
graphics card alone. This document is the whole story, because working it out
from scratch cost the best part of a day.

If the screen goes black after "Loading initial ramdisk …", read §1.

---

## 1. The fault

The Radeon X1900 XT in this machine is a **Mac edition** card. Its ROM is an
EFI ROM, not a legacy x86 VBIOS, so it has no `0xAA55` signature. The kernel's
`radeon` driver insists on finding one:

```
radeon 0000:08:00.0: vgaarb: deactivate vga console
radeon 0000:08:00.0: Invalid PCI ROM header signature: expecting 0xaa55, got 0xffff
[drm:radeon_get_bios [radeon]] *ERROR* Unable to locate a BIOS ROM
radeon 0000:08:00.0: Fatal error during GPU init
radeon 0000:08:00.0: probe with driver radeon failed with error -22
```

Read the order of those lines carefully. `radeon` **deactivates the VGA console
first**, then fails. Nothing takes the console back, so the display dies while
the machine carries on booting perfectly normally.

That is the entire "unbootable Linux" symptom. The machine was never hanging —
it reached multi-user, brought up networking and sshd, and sat there for over an
hour and a half with a black screen.

**Diagnostic tell:** if it looks dead, ping it. If it answers, it booted and
this is your problem.

## 2. The fix

Keep `radeon` off the card and let the firmware framebuffer drive the console.

`/etc/default/grub`:

```
GRUB_CMDLINE_LINUX_DEFAULT="nomodeset"
GRUB_GFXPAYLOAD_LINUX=text
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=5
```

`/etc/modprobe.d/blacklist-radeon.conf`:

```
blacklist radeon
```

Then `update-grub`. Result:

```
$ cat /sys/class/graphics/fb0/name
EFI VGA
$ cat /sys/class/graphics/fb0/virtual_size
2560,1440
```

A working 2560×1440 text console, and no `radeon` in `lsmod` at all.

## 3. `gfxpayload` must be pinned to `text` — unset is nearly as bad as `keep`

This caused a second, longer hunt after the memory fault was fixed, so it is
worth stating precisely.

**Symptom:** cold boot, press Enter on the GRUB menu, a single underscore
appears, then black. No kernel output at all, no network, fans quiet, and **no
`T_FAULT`** — so it is not the memory fault in §11. Roughly **two cold boots in
three** failed this way; the third would boot perfectly.

**Proof it never reached userspace:** `journalctl --list-boots` showed no record
whatsoever for the failed attempts. The kernel was hanging before journald
started.

**Cause:** the ESP boot menu did not set `gfxpayload` at all. Debian's own
`/etc/default/grub` had `text`, but the ESP menu is what actually boots this
machine, and there GRUB was free to choose. An unpinned handover hangs the
kernel before it prints a character — intermittently, which is what made it so
hard to pin down.

**Fix**, now present both globally and inside `find_debian` in
`/boot/efi/EFI/BOOT/grub.cfg`:

```
set gfxpayload=text
```

If you ever rebuild that menu, keep it. Test it by cold booting three times, not
once: a single success proves nothing when the failure rate is 2 in 3.

**Honest status: pinning it did NOT fix the intermittent failure.** Testing over
six cold boots gave roughly the same success rate as before (about 1 in 3-5).
The setting is correct and worth keeping -- an unpinned handover is genuinely
unsafe on this firmware -- but it is not the cause of the intermittency. The
cause is still unknown. See §13.

## 3b. Do NOT set `GRUB_GFXPAYLOAD_LINUX=keep`

This is worth its own section because it wasted hours and looks like the
opposite problem.

`keep` makes GRUB hand its own graphics mode to the kernel. On this machine's
32-bit EFI that handover **hangs the kernel instantly**, right after GRUB prints
"Loading initial ramdisk …". You get two lines and a dead cursor, with no
network — a genuine hang, unlike §1.

Use `text`. If you ever see the machine stop dead on those two lines, this
setting is the first thing to check.

## 4. Keep `quiet` out of the command line

Debian ships `GRUB_CMDLINE_LINUX_DEFAULT="quiet"`. On a machine whose display
is this fragile, `quiet` makes a healthy boot and a hung boot look identical —
both show only GRUB's last two lines.

Leaving `quiet` off costs nothing and means you can always see where a boot
stopped. It is deliberately absent from the config above.

## 5. The desktop

There is **no DRM device** (`/dev/dri` does not exist) because no KMS driver
binds the card. So Xorg cannot use `modesetting` or `radeon` — it must use
`fbdev` against the EFI framebuffer.

`/etc/X11/xorg.conf.d/20-fbdev.conf`:

```
Section "Device"
    Identifier  "EFI framebuffer"
    Driver      "fbdev"
    Option      "ShadowFB" "true"
EndSection
```

XFCE + lightdm then run at 2560×1440. Confirmed working, with the Magic
Keyboard and Logitech M720 picked up by `libinput`.

Expect it to be **slow**: this is an unaccelerated shadow framebuffer pushing
3.7 megapixels with a 2006 CPU. It is fine for a browser and a terminal. It is
not fine for video. For real 2D/3D acceleration you need a different graphics
card — see [HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md).

If you would rather not run a desktop at all:

```bash
sudo systemctl set-default multi-user.target
```

## 6. The bootloader on the ESP

`/boot/efi/EFI/BOOT/BOOTIA32.EFI` is a **hand-built 32-bit GRUB** (593,920
bytes) carrying modules Debian's own loader lacked in this situation —
`ext2`, `probe`, `regexp`, `search_fs_file`. Its menu lives at
`/boot/efi/EFI/BOOT/grub.cfg`.

It finds the kernel by wildcard and derives the initrd version from it by
regex, so **it keeps working after kernel upgrades** — nothing is hardcoded.

Entries:

| # | Entry | Use |
|---|---|---|
| 1 | Debian GNU/Linux (normal) | default |
| 2 | repair filesystem (forced fsck) | after a power cut |
| 3 | emergency shell | last resort |
| 4 | full menu from disk | Debian's own menu, all kernels, Mac OS X |
| 5 | Show what was found | prints device, UUID, kernel, initrd |

Entry 5 is genuinely useful when something is wrong and you cannot read the
disk from anywhere else.

Backups kept alongside it:

- `BOOTIA32.EFI.debian-orig` — Debian's own `grubia32.efi` (106,496 bytes)
- `BOOTIA32.EFI.grub-repair` — a copy of the loader in use

To go back to Debian's stock loader:

```bash
cd /boot/efi/EFI/BOOT
sudo cp -p BOOTIA32.EFI.debian-orig BOOTIA32.EFI
```

That is safe **only** once `/etc/default/grub` holds the settings in §2, because
Debian's loader reads `/boot/grub/grub.cfg` instead of the ESP menu.

## 7. Machine facts worth having written down

```
root filesystem : ext4, UUID 9ebf7afb-2b9f-4c0d-aa88-d9f542f60901  (GRUB: hd1,gpt2)
ESP             : vfat,  mounted at /boot/efi
swap            : 6 GB   (same disk as root)
Mac OS X (Lion) : hfsplus, label "Lion", 931 GB  -- do not touch

*** DEVICE LETTERS ARE NOT STABLE. sda and sdb swap between boots: they were
    Debian=sda/Lion=sdb, then after a hardware reseat became Lion=sda/Debian=sdb.
    Never write a command against a letter. Always check first:
        lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT
    and address disks as /dev/disk/by-label/Lion or by UUID. ***
kernel          : 6.12.101+deb13-amd64  (6.12.94 also installed as fallback)
hostname/user   : macpro / macpro
GPU             : 08:00.0 R580 [Radeon X1900 XT] [1002:7249]
CPU             : 2x Xeon 5150 "Woodcrest" -- x86-64-v1, no SSE4.1/SSE4.2/POPCNT
RAM             : 8 GB DDR2 FB-DIMM ECC (8x1GB, all slots). NOTE: DIMM A4 had a
                  marginal contact that broke every Linux boot -- see §11
```

**Disk naming has caused real mistakes here, twice.** The letters are assigned in
whatever order the SATA controller enumerates, and that order has already changed
once on this machine. Identify by **partition count and filesystem**, which do not
change:

```
three partitions, ext4 + vfat + swap   -> Debian
two partitions,   vfat + hfsplus       -> Lion
```

Earlier versions of this document hardcoded `/dev/sdb2` as Lion. After the
letters swapped, that same command pointed at Debian's root. Use labels.

## 8. Node.js — why the distro package matters

The CPUs are **x86-64-v1**: no SSE4.1, SSE4.2 or POPCNT. Official Node.js
binaries from nodejs.org are built for newer baselines and die with an illegal
instruction here.

**Debian's `nodejs` package works**, because Debian builds for the x86-64
baseline:

```
$ node -e 'console.log(process.version)'
v20.19.2
```

So install Node from apt, never from nodejs.org or `nvm`. The npm-based AI CLIs
(Claude Code, Gemini CLI) run fine on top of it.

Same reasoning applies generally: prefer Debian packages over upstream binaries
on this machine, and if something dies instantly with SIGILL, this is why.

### Claude Code must stay on the 1.x line

This one bites hard and silently. **Claude Code 2.x ships as a precompiled
native binary**, not a JS script, and it is built for a newer x86-64 baseline:

```
$ claude --version
Illegal instruction        (rc=132)
$ dmesg | tail -1
traps: claude[9217] trap invalid opcode ip:1b8fe99 in claude.exe[...]
$ head -c 8 /usr/local/bin/claude
ELF>...
```

**1.0.128 is the newest release that is still plain JavaScript**, and it runs
perfectly on Debian's Node:

```
$ head -1 /usr/local/bin/claude
#!/usr/bin/env node
$ claude --version
1.0.128 (Claude Code)
```

Installed and working. Do not upgrade it:

```bash
sudo npm install -g @anthropic-ai/claude-code@1.0.128    # if it ever gets replaced
```

The auto-updater is disabled **two** ways, and both matter — Claude Code's own
config defaults to `autoUpdates: true` and would override a bare env var:

```bash
# 1. system-wide environment
cat /etc/profile.d/99-claude-code-pin.sh     # DISABLE_AUTOUPDATER=1

# 2. Claude Code's own config
claude config get -g autoUpdates             # "false"
```

**Leave both in place** — without them Claude Code quietly updates itself to 2.x
and stops working, with only an "Illegal instruction" to explain why.

Verified working state:

```
version     : 1.0.128 (Claude Code)
theme       : "dark"
autoUpdates : "false"
```

Gemini CLI (`@google/gemini-cli`) is unaffected — still JavaScript, runs fine.

If you ever want current Claude Code on this box, the options are: a newer CPU
(§HARDWARE-UPGRADE-PATH — Harpertown Xeons have SSE4.1), or drive the Anthropic
API directly from Python, which is CPU-agnostic. The kit's `aigw.py` gateway in
`kit/gateway/` already does exactly that and was written for this constraint.

### aider is not installed

`pipx install aider-chat` fails during the wheel build. The cause is Python
version, not the CPU: Debian 13 ships **Python 3.13 only**, and aider-chat
does not yet support it.

Nothing to do about it cleanly on trixie. If you want aider, the least-bad
route is a Python 3.12 built alongside (`pipx install --python python3.12
aider-chat`), which means building 3.12 yourself. Given `claude` and `gemini`
both work, this is probably not worth it.

### AI tooling: what actually works here

| Tool | Status | Notes |
|---|---|---|
| `claude` | **works** | Claude Code **1.0.128**, pinned; 2.x is native and SIGILLs |
| `gemini` | **works** | Gemini CLI 0.55.1, plain JS |
| `aider` | not installed | needs Python < 3.13 |
| `aigw.py` | works | pure-stdlib Python gateway in `kit/gateway/`, CPU-agnostic |

Both working CLIs need API credentials before they do anything useful —
`ANTHROPIC_API_KEY` and `GEMINI_API_KEY` respectively.

## 9. Intermittent no-video at power-on — likely hardware

Separate from everything above, and **not fixable in software**.

On roughly every other cold boot the machine powers up with no video at all and
the fans ramp to full and stay there — the firmware failing to initialise video
during POST, before any bootloader runs.

Evidence pointing at the graphics card:

- the card's ROM reads back as `0xffff` (§1) — the signature of a device not
  responding, rather than a wrong value
- the fault is intermittent, which is how a marginal card behaves
- it began after a mains power cut
- memory tests clean (all 6 DIMMs `Status: OK`, ECC enabled, zero panics), both
  1 TB drives healthy, and the OS runs for hours once booted

Cheap things to try first: **reseat the graphics card and the FB-DIMMs.**
Oxidised contacts after a power event are common and free to rule out.

If it persists, the fix is a replacement card. A Mac-flashed Radeon HD 5770 or
similar also gets you boot screens, a working `radeon`/`amdgpu` driver, real
acceleration, and makes this entire document obsolete. See
[HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md).

## 10. Before handover — revoke automation access

Remote administration was granted so this machine could be fixed over SSH. It
should not ship that way:

```bash
sudo rm /etc/sudoers.d/90-macpro-automation
sudo sed -i '/^macpro ALL=(ALL) NOPASSWD:ALL$/d' /etc/sudoers
sudo visudo -c
```

The rule exists in **both** places — a `sudoers.d` drop-in and a line appended
to `/etc/sudoers` — so remove both. Run `visudo -c` afterwards to confirm the
file still parses; a broken `/etc/sudoers` locks everyone out of sudo.

Also remove the remote key:

```bash
sed -i '/aaryn.alexander@gmail.com/d' ~/.ssh/authorized_keys
```

`macpro` stays in the `sudo` group and will simply be asked for a password,
which is the normal Debian arrangement.

---

# 11. Linux dies with NO output at all, and the fans stay loud

This is a different fault from §1, it is **hardware**, and it cost a week to
find. Read this before touching any software.

## Symptoms

- GRUB menu appears and works normally
- You press Enter and get a **single underscore, then black** — no kernel
  messages at all, not even with `nomodeset`
- **Fans ramp to full after the chime and never settle**
- On roughly every other cold boot there is no video whatsoever
- A **red LED labelled `T_FAULT`** is lit on the horizontal board at the front
  of the case, below the fan and graphics card
- Mac OS X **still boots fine**, which is deeply misleading

## Cause: a marginal FB-DIMM contact

`T_FAULT` is the thermal fault indicator. FB-DIMMs carry an AMB buffer chip that
runs hot, and this model's memory risers are marginal on airflow when fully
populated. A DIMM making poor contact overheats, the SMC raises `T_FAULT`, pins
the fans, and the machine becomes unstable in a way that kills Linux before the
console initialises.

**On this machine it was DIMM A4** — reseating that one stick fixed it, with all
eight sticks working afterwards. The contacts are twenty years old; oxide film
plus heat is enough.

**Why Mac OS X survives and Linux does not:** Lion touches a fraction of the
installed memory. Linux reads all of it during early boot, which is exactly
where these boots die. A working macOS boot does **not** clear the memory.

If it gets far enough to run a kernel you may see a panic like this, which is
the same fault one notch less severe:

```
CPU: 3  PID: 345  Comm: modprobe   Tainted: G D L
RIP: 0010:do_user_addr_fault+0xce/0x520
     __get_user_8+0x18/0x30
Code: Unable to access opcode bytes at 0x7f4eb5718978
```

A page fault *inside* the page-fault handler, with "unable to access opcode
bytes", in an unrelated process. That is bad memory, not a driver.

## Fixing it

Slots pair as **1+2** and **3+4** on each riser. A pair must be complete or the
firmware may ignore it — filling 1,2,3 and leaving 4 empty can quietly run as
four sticks.

1. **Reseat everything first.** Press until the clips at *both* ends snap up on
   their own. This alone fixed it here, and also recovered two sticks that had
   not been registering at all (6 GB became 8 GB).
2. If it still fails, **bisect by pair.** Fill `A1,A2,A3,A4` + `B1,B2`. Boots?
   The fault is in the pair you left out. Fails? It is in `A3`/`A4`.
3. To find the single stick, put **one** suspect back beside a known-good one.
   Boots means the one you inserted is good.
4. Mark the sticks with tape as you go.

With one genuinely dead stick you can still run three complete pairs (6 GB) and
keep a spare. 1 GB FB-DIMMs are cheap secondhand.

## Watch for it recurring: ECC via rasdaemon, not EDAC

**EDAC cannot work on this machine.** The chipset is an Intel 5000X and Debian's
kernel no longer ships `i5000_edac` — it has `i5100`, `i5400` and `i7300` but
not `i5000`. So `/sys/devices/system/edac/mc` stays empty forever, and the
obvious instrument reads as "healthy" when it is simply *absent*. That misled
this investigation for days.

`rasdaemon` reads corrected and uncorrected memory errors from the CPU's
machine-check banks instead, which needs no EDAC driver:

```bash
sudo apt install rasdaemon
sudo systemctl enable --now rasdaemon
sudo ras-mc-ctl --summary        # want: "No Memory errors."
```

It is installed and enabled, and `macpro-telemetry` reports it, so the cockpit's
Status tab shows it. **A rising correctable count is the early warning** — it
appears days before anything panics. If this fault had been instrumented from
the start it would have been an afternoon, not a week.

## Debugging lesson worth keeping

`ping` is not a boot test if you have not confirmed the machine is awake and
powered. Several conclusions in this investigation were drawn from silence that
turned out to be a sleeping machine running the *other* OS. Check
`last reboot` and `pmset -g log` on the macOS side before concluding a Linux
boot failed.

And when Linux fails but macOS boots, **suspect memory before software.** The
asymmetry is a symptom, not a contradiction.


---

# 12. The clock is 4 hours out after switching OS

Lion writes **local time** to the hardware clock; Debian expects **UTC**. So each
one leaves the RTC in a form the other misreads, and early boot timestamps land
4 hours in the future — visible as `journalctl --list-boots` showing a FIRST
ENTRY later than its LAST ENTRY.

Debian is now configured to treat the RTC as UTC, which matches what it
contains:

```bash
sudo timedatectl set-local-rtc 0 --adjust-system-clock
timedatectl        # want: "RTC in local TZ: no"
```

Both systems run NTP, so both correct themselves within a minute of booting.
The only lasting artifact is odd timestamps in the first moments of a boot log.
Harmless, but worth recognising rather than chasing.


---

# 13. Intermittent failure to boot at all — still open

**Symptom.** From cold, roughly **one boot in three to one in five** reaches
Debian. The others show a single underscore after Enter on the GRUB menu, then
black. No kernel output, no network, fans quiet, chime normal, and **no
`T_FAULT`** — so this is NOT the memory fault in §11, which was fixed.

**What is proven, not guessed:**

- `journalctl --list-boots` shows **no record at all** for failed attempts, so
  the kernel never reaches userspace.
- On a failed boot, **a single tap of the power button switches the machine
  off**. A successful boot needs a 10-second hold. A running OS traps that
  button; so on a failure there is genuinely no OS running.
- Both drives are healthy: the Debian disk has 0 pending sectors, 0
  uncorrectable, no filesystem errors.
- Memory tests clean, ECC reports no errors on boots that succeed.
- **Mac OS X Lion boots reliably every time**, which is the most puzzling part.

**Ruled out** (each tested, each wrong):

| Theory | How it was eliminated |
|---|---|
| DHCP blocked by nftables | masked the firewall; no change |
| Bad memory | reseating fixed `T_FAULT` and the fans, but not this |
| `graphical.target` / lightdm | booted `multi-user.target`; no change |
| Unpinned `gfxpayload` | pinned to `text`; success rate unchanged |
| Disk read failure | SMART clean, no ext4 errors, GRUB reads fine |

**Still plausible:** the power supply. It is 19 years old, ageing electrolytic
capacitors are this model's second failure mode after the FB-DIMMs, and
intermittent failure-to-start is the classic symptom. `autorestart` being on
explains the machine powering up when mains is reconnected — that part is a
setting, not a fault.

## The instrument to use next

Every boot entry now carries `earlyprintk=efi,keep`, and there is a dedicated
entry:

```
Debian - VERBOSE diagnostic (use when a boot fails)
```

`earlyprintk` writes to the firmware framebuffer from the kernel's **first
instruction**, before the normal console exists. So a failing boot should now
print something and then stop, instead of showing a bare cursor.

**When a boot fails, photograph the last line on screen.** That single line is
worth more than any further theorising — it names what the kernel was doing when
it stopped. If nothing prints even with `earlyprintk`, the kernel is not
executing at all, and the investigation moves to the power supply and the logic
board rather than software.

**Workaround in the meantime:** it does boot, it just takes patience. Power off
fully and try again; two or three attempts usually get there. Once up it is
completely stable — uptimes of many hours with zero failed units.

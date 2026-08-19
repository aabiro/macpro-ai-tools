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

## 3. Do NOT set `GRUB_GFXPAYLOAD_LINUX=keep`

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
root filesystem : /dev/sda2  ext4   (GRUB: hd1,gpt2)
root UUID       : 9ebf7afb-2b9f-4c0d-aa88-d9f542f60901
ESP             : /dev/sda1  vfat   mounted at /boot/efi
swap            : /dev/sda3  6 GB
Mac OS X (Lion) : /dev/sdb2  hfsplus 931 GB   -- do not touch
kernel          : 6.12.101+deb13-amd64  (6.12.94 also installed as fallback)
hostname/user   : macpro / macpro
GPU             : 08:00.0 R580 [Radeon X1900 XT] [1002:7249]
CPU             : 2x Xeon 5150 "Woodcrest" -- x86-64-v1, no SSE4.1/SSE4.2/POPCNT
RAM             : 6 GB DDR2 FB-DIMM ECC, all 6 sticks Status: OK
```

**Disk naming is counter-intuitive and has caused mistakes:** Linux calls the
Debian disk `sda` and the Lion disk `sdb`, which is the opposite order to macOS,
where Lion is `disk0`. Confirm by partition count — Debian's disk has three
partitions, Lion's has two:

```
sda: sda1 sda2 sda3      <- Debian
sdb: sdb1 sdb2           <- Lion
```

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

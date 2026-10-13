# Linux Starter Pack — Mac Pro 1,1 (2006)

Turning this machine into a modern, AI-capable computer.

---

## Why you would want to

Mac OS X Lion on this machine is a museum piece with a real problem: it cannot
speak modern encryption (TLS 1.2+), so most of the internet is closed to it.
The AI Cockpit works around that with a helper program on another computer.

Installing Linux removes the problem entirely rather than working around it:

| | Lion (as shipped) | Linux (after this guide) |
|---|---|---|
| Modern websites | Mostly fail | Work |
| AI services | Only via the gateway helper | Direct, no helper needed |
| `claude`, `gemini`, `aider` CLIs | Cannot run | Run natively |
| Docker / containers | No | Yes |
| Current dev tooling | No | Yes |
| Security updates | Ended 2014 | Current |

The machine is 4 cores and 6 GB of RAM. That is a perfectly respectable Linux
box for coding, self-hosting, and running an always-on service.

**Your Lion install is not destroyed by this.** Linux goes on the *second*
drive. You pick which one to boot by holding **Option** at startup.

---

## The one hard part, explained

This machine has a **64-bit processor but a 32-bit EFI firmware**. Verified on
this exact machine:

```
$ ioreg -l -p IODeviceTree | grep firmware-abi
      "firmware-abi" = <"EFI32">
```

Almost every modern Linux USB installer is built for 64-bit UEFI. This machine
cannot boot those. It is the single reason people give up on installing Linux on
a 2006 Mac Pro, and it has nothing to do with the CPU being too old.

You have two ways around it. **Route A is strongly recommended.**

### Route A — Boot the installer from a DVD (recommended)

This machine has a working DVD burner (OPTIARC AD-7170A, verified). Booting a
burned DVD uses the legacy BIOS path, which sidesteps the 32-bit EFI problem
completely. It is the highest-success route and needs no special tooling.

### Route B — USB with a 32-bit EFI bootloader

Possible, but fiddly: the USB must carry an `ia32` EFI bootloader
(`grub-efi-ia32` or rEFInd). A plain `dd` of a standard ISO to USB will **not**
appear in the boot picker. Only attempt this if you have no blank DVDs.

---

## What you need

- A blank DVD-R (this machine burns them; almost any other computer can too)
- A wired Ethernet connection — the 2006 AirPort card is 802.11g and its Linux
  driver support is poor. **Plug in a network cable.**
- About 90 minutes
- **A backup of anything on this machine you care about**, taken first

---

## Choosing a distribution

**Debian 13 ("trixie"), 64-bit, is the recommendation.** It is the least
demanding on old hardware, has the best support for 32-bit EFI Macs, and its
installer can place the right bootloader.

Avoid: Ubuntu Desktop (its installer assumes 64-bit UEFI and the GNOME desktop
will be sluggish on a Radeon X1900), and anything requiring Secure Boot.

Desktop choice — this machine has an ATI Radeon X1900 XT (512 MB, 2006):

- **XFCE** — recommended. Light, complete, works well with the old `radeon` driver.
- **No desktop (server)** — best if you only want SSH and containers.
- Avoid GNOME and KDE Plasma.

---

## Step 1 — Back up, and confirm your safety net

The second drive currently holds a volume named **Liferaft**: a full clone of
this Lion system. Installing Linux over it **destroys that clone.**

Before you continue, decide honestly:

- If you may ever want Lion restored, copy Liferaft off to an external drive first.
- If you do not care about Lion, continue.

Confirm what you are about to overwrite — in Lion's Terminal:

```bash
diskutil list
```

You should see `disk1` containing `Liferaft`. **`disk1` is the drive Linux will
take. `disk0` holds your working Lion system — do not touch it.**

> Verify the identifiers on the day. If a drive has been added, removed, or
> reseated, the numbering can shift, and installing to the wrong one erases
> your Lion system.

---

## Step 2 — Get the installer image

**Use Debian's Mac-specific image.** Debian publishes a separate build carrying a
**32-bit EFI bootloader**, made for exactly the `EFI32` problem above:

```
debian-mac-13.6.0-amd64-netinst.iso     <- USE THIS ONE
debian-13.6.0-amd64-netinst.iso         <- the standard image; 64-bit EFI only
```

Get it from the `iso-cd` directory of the current release:

<https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/>

Note the `debian-mac-` prefix. It is easy to grab the standard image by mistake,
and it will simply not appear in this machine's boot picker.

Verify the download before burning — a corrupt ISO wastes a disc and an hour:

```bash
curl -sO https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing
```

Burn it to a DVD **as a disc image** — not as a data file. Any burning tool's
"Burn image to disc" option is correct. On a Mac:

```bash
hdiutil burn debian-mac-13.6.0-amd64-netinst.iso
```

Debian 13 still targets baseline `amd64` (x86-64-**v1**), which is what this
Xeon 5150 is. That is why Debian works here and Ubuntu 26.04 does not — see the
runbook's Blocker B.

---

## Step 3 — Boot the installer

1. Put the DVD in the Mac Pro.
2. Restart, and hold **Option (Alt)** immediately, keeping it held.
3. The boot picker appears. Choose the DVD — it may be labelled
   **"Windows"**. That label is normal and expected: it is the generic icon for
   any non-Apple bootable disc.
4. At the Debian boot menu, choose **Install** (the plain text installer is more
   reliable here than the graphical one).

If the DVD does not appear in the picker, the burn was written as a data file
rather than as an image. Re-burn it.

---

## Step 4 — Install

Follow the prompts. The parts that matter:

**Network** — use the wired Ethernet connection.

**Partitioning** — this is the step where care pays off.

- Choose **Guided — use entire disk**.
- Select the **1 TB disk that is NOT your Lion system**. Cross-check the size
  and model against what `diskutil list` told you in Step 1.
- If the installer offers "use entire disk and set up LVM", plain (non-LVM) is
  simpler to recover later.

**Software selection** — with the space bar, select:

- `XFCE` (or nothing at all, for a server)
- `SSH server` ← select this, it is how you will manage the machine remotely
- `standard system utilities`

Deselect `GNOME` if it is pre-selected.

**Bootloader** — install GRUB to the drive you just partitioned, **not** to the
Lion drive.

---

## Step 5 — First boot

Hold **Option** at startup and pick the Linux drive. Log in, open a terminal,
and confirm you have a network:

```bash
ping -c3 debian.org
```

Then run the starter pack script (Step 6). If the graphical desktop fails to
start and you get a black screen, boot again and at the GRUB menu press `e`,
add `nomodeset` to the end of the `linux` line, and press Ctrl-X. Fix it
permanently later with `radeon.modeset=1` in `/etc/default/grub`.

---

## Step 6 — Run the starter pack

This provisions the machine as a modern AI-capable development box: current
toolchains, Docker, and the AI command-line tools.

Copy `bootstrap.sh` onto the machine (USB stick, or `scp` from another
computer), then:

```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

Preview everything it would do without changing anything:

```bash
./bootstrap.sh --dry-run
```

Pick and choose:

```bash
./bootstrap.sh --no-docker --no-ollama
./bootstrap.sh --help
```

---

## Step 7 — Connect your AI tools

After the bootstrap, you have `claude`, `gemini`, and `aider` available.

```bash
claude
```

On first run it walks you through signing in. From then on, you can drive and
program this machine conversationally — which is the whole point of the exercise.

Note the difference from Lion: **no gateway is needed here.** Linux has modern
TLS, so these tools talk to the services directly.

---

## Realistic expectations

This is a 2006 machine. Being straight with you about what it is and is not:

**Good at:** SSH server, Docker services, web/API development, file server,
scripting, running AI *command-line* tools that call cloud services (the network
does the heavy lifting, not this CPU).

**Poor at:** Running AI models locally. The bootstrap can install Ollama, but
with 6 GB of RAM, no usable GPU, and 2006-era CPU cores, expect roughly 1–3
tokens per second on a small 3B model. It works, and it is a fun thing to try
once, but it is not a practical way to get work done. Use the cloud CLIs.

**Also poor at:** modern video, 4K anything, and current AAA-era games.

**Power draw:** this tower idles around 150–200 W. As an always-on server that
is roughly £15–25 / $20–30 a month in electricity. A Raspberry Pi does many of
the same jobs for a fraction of that. Worth knowing before committing it to
24/7 duty.

---

## If you want to go further

**Dual-boot menu instead of holding Option:** install rEFInd on the Lion side
for a graphical boot picker on every start. <https://www.rodsbooks.com/refind/>

**Serve the vintage side:** if you get another vintage Mac, this Linux install
can run `aigw.py` (in `/Users/Shared/ai-cockpit/gateway/` on the Lion drive) as
a permanent service, giving that machine AI access. Note it cannot do this for
*this* machine's Lion system, since only one operating system runs at a time.

**More memory:** this model takes DDR2 FB-DIMMs in matched pairs, up to 32 GB.
They are cheap secondhand now. They also run hot — if you add memory, keep the
heatsinks on and the dust out.

# Using Linux and Mac OS X Lion together

Two operating systems are installed on two separate hard disks. This explains
what you can and cannot do across them, because the answer is not symmetrical
and the asymmetry surprises people.

## The basic rule: one at a time on the metal

**Only one of them owns the hardware at any moment.** You choose at power-on,
from the boot menu. There is no way to switch without restarting, and while
Linux is running, Lion is not running *on the hardware* — its programs are not
available, its services are not answering.

Two things get around that, and both are covered below:

- Lion's **files** can be read from Linux at any time. See the next section.
- Lion itself can be **run as a virtual machine** while Linux is running, which
  gives you a root shell in Lion from a Linux terminal. See
  [Lion runs inside Linux](#lion-runs-inside-linux-in-a-virtual-machine).
  It does not touch the real Lion disk at all.

So "Lion is unreachable while Linux runs" is no longer quite true. What remains
true is that only one of them can *own the machine* at a time.

## What works: Linux can read Lion's files

While Linux is running, Lion's entire disk can be read. Verified — 233 GB of it:

```bash
sudo mount /mnt/lion
ls /mnt/lion/Users
```

`/etc/fstab` already has the entry, so that short command is all it takes. When
finished:

```bash
sudo umount /mnt/lion
```

**It is mounted read-only on purpose, and you should leave it that way.** Two
independent reasons:

1. That disk has **2,839 recorded uncorrectable reads** and pending sectors. It
   is failing. Writing to a failing disk is how you turn "some files are
   unreadable" into "the volume will not mount".
2. Linux's HFS+ write support is not trustworthy, and Lion's journal is dirty.
   Writing through it can corrupt the filesystem even on a healthy disk.

So: read from Lion, copy *out* of it, and write nothing back. See
[DISK-HEALTH-AND-BACKUP.md](DISK-HEALTH-AND-BACKUP.md).

## What does not work: Lion cannot read Linux's files

Mac OS X has no support for **ext4**, the filesystem Linux uses. Booted into
Lion, the Linux disk simply is not readable. Lion may offer to initialise it —
**say no.** That would erase Linux.

So the sharing is one-directional out of the box: Linux reaches into Lion, not
the other way round.

## Making a two-way shared space

If you want to move files *both* ways, give the two systems a filesystem they
both understand. **exFAT** is the one to use: Lion supports it (Mac OS X has
since 10.6.5) and the tools are installed here (`exfatprogs`).

You need somewhere to put it — a **USB stick or a spare internal drive**, not a
slice of either existing disk. This machine takes four drives and two bays are
free, so an internal one is the tidy option.

With the new drive plugged in, and having checked carefully which device it is:

```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT        # LOOK. Every time.
sudo mkfs.exfat -n SHARED /dev/sdX1               # replace sdX1
sudo mkdir -p /mnt/shared
sudo mount /dev/disk/by-label/SHARED /mnt/shared
```

> **Identify the disk by label or size, never by letter.** On this machine `sda`
> and `sdb` swap between boots. `mkfs` on the wrong letter destroys whatever was
> there, and one of the two disks holds the only copy of the previous owner's
> files.

Once you have done that — it does not exist until you do — both systems can
read and write `/mnt/shared` (Linux) and the `SHARED`
volume (Lion).

## The AI tools: why Lion needs help from elsewhere

This is the one genuinely awkward consequence of one-at-a-time.

The `g5-codex`, `g5-copilot` and `g5-gemini` commands on the Lion side work by
asking a **gateway** to do the encrypted part of talking to an AI provider —
because Lion's 2011-era OpenSSL cannot negotiate TLS with any modern service.

That gateway runs on **this machine's Linux side**. Which is not running when
Lion is.

So Lion's AI tools need a gateway on **some other computer that is switched on**
— a laptop, a Raspberry Pi, anything with Python 3. The gateway is a single
file, `aigw.py`, and needs no libraries beyond the standard library:

```bash
# on the other machine, once:
export GEMINI_API_KEY=...
python3 aigw.py --port 8081
```

Then on Lion, point the tools at it:

```
g5-config set gateway http://<that-machine>:8081
g5-config test
```

`g5-config test` reports whether the gateway answered and which providers it has
keys for, which turns "it doesn't work" into a specific fault.

Full detail in [AI-STACK.md](AI-STACK.md).

## Lion runs inside Linux, in a virtual machine

This used to say "don't bother." It now works, so here is how to use it.

Lion boots as a guest while Linux keeps running. You get a root shell in Mac OS
X 10.7.5 from a Linux terminal, without restarting anything:

```
lion-vm start          # about 60 seconds to ready
lion-vm wait           # blocks until it answers
lion sw_vers           # run anything, as root, inside Lion
lion-vm stop           # clean shutdown, about 12 seconds
```

`lion` on its own gives an interactive shell. `lion-vm` on its own lists
everything it can do.

### The part that matters most: the real disk is never written

Lion's disk is the one that is failing — 255 reallocated sectors and 4 pending.
So the VM does not use it directly. The physical disk is the *backing file* of
a copy-on-write overlay and QEMU opens it **read-only**. Every write the guest
makes — including its own `fsck` repairs and journal replay — lands in
`/var/lib/lion-vm/lion-overlay.qcow2` instead.

This is not a claim, it is checkable. After every boot, the disk's HFS+ volume
header still reads `0x80002000` and its SMART counters have not moved, while
the overlay has grown to around 900 MB. `lion-vm status` shows you the same
thing.

The practical consequence: **experiments in the VM cannot damage Lion.** Break
it however badly you like, then `lion-vm restore`.

### What it is good for, and what it is not

Good for: running commands in Lion, reading and changing its files, testing a
fix before doing it for real, and letting an AI assistant work on Lion — which
was the whole point, because Lion itself is too old to run modern AI tooling.

Not good for: using Lion as a desktop. Two honest limits —

| | |
|---|---|
| No visible desktop in a normal boot | 10.7 has no driver for the virtual display, so the screen stays black even though the OS is running fine underneath. Harmless if you are working over `lion`. |
| A desktop only in safe mode | `lion-vm start --safe` does draw the login window; connect a VNC viewer to `127.0.0.1:5901`. Safe mode disables plenty, so treat it as a look-around, not a working environment. |
| Slower than bare metal | These Xeons predate EPT, so KVM emulates memory management in software. Fine for shell work; not for anything heavy. |
| Licensing is fine | Apple permits virtualising 10.7 on Apple hardware, which this is. |

For a *fast desktop* Lion, restart into it on real hardware — that is still the
better tool for that job, and it is one restart away.

### The SSH access lives in the overlay, not on the disk

Remote Login was switched on, and the access key installed, **inside the
overlay**. The real Lion install on the disk is untouched and still has Remote
Login off. So:

- `lion-vm snapshot` keeps a copy of the working overlay. One exists already.
- `lion-vm restore` puts it back — use this to undo VM damage.
- `lion-vm reset` goes all the way back to the bare disk, which also removes
  the SSH access. You would then have to set it up again; the procedure is in
  [LION-VM.md](LION-VM.md).

The key is an RSA key generated on this machine, and it stays on this machine.
Password logins are refused outright on that path (`PasswordAuthentication no`).

The reverse — Linux as a guest inside Lion — is still not worth attempting:
Lion's era of VirtualBox and VMware are long unsupported, and the Linux install
here is on bare metal rather than in a disk image.

Full technical record, including the five separate problems that had to be
solved to make it boot at all: [LION-VM.md](LION-VM.md).

## Which side to use for what

| | |
|---|---|
| **Linux** | Everything current: the AI tools, the browser, the editor, LibreOffice, video, containers, anything needing the internet. This is where to live. |
| **Lion** | Old Mac software that only exists for Mac OS X, and reaching the previous owner's files in their original environment. |

Lion is genuinely unsafe to browse the web on — it stopped receiving security
updates around 2014, and no current browser supports it. Use Linux for anything
that touches the internet.

To **write code for Lion**, you do not have to choose sides: VS Code on Linux can
edit Lion's own files and run them inside Lion, with an AI assistant doing the
work. That workflow has its own page —
[LION-DEV-QUICKSTART.md](LION-DEV-QUICKSTART.md).

## Choosing at boot

The boot menu appears at power-on. If you miss it, restart. Details, including
what to do about a black screen, are in
[LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md).

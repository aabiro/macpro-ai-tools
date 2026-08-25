# Using Linux and Mac OS X Lion together

Two operating systems are installed on two separate hard disks. This explains
what you can and cannot do across them, because the answer is not symmetrical
and the asymmetry surprises people.

## The basic rule: one at a time

**Only one of them runs at any moment.** You choose at power-on, from the boot
menu. There is no way to switch without restarting, and while Linux is running,
Lion is not running — its programs are not available, its services are not
answering, nothing on that side is executing.

That is what "Lion is unreachable while Linux runs" means: unreachable as a
*running system*. Its **files** are a different matter.

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

Both systems can then read and write `/mnt/shared` (Linux) and the `SHARED`
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

## Could Lion run inside Linux, in a virtual machine?

Asked often enough to answer properly. The honest answer is *possible in
principle, poor value in practice.*

**The hardware allows it.** These Xeons have Intel VT-x, and `/dev/kvm` is
present and working on this machine — checked, not assumed.

**But they lack EPT.** Nested paging arrived with the Nehalem generation, a
couple of years after this machine. Without it, KVM has to emulate memory
management in software, and everything inside the virtual machine runs
substantially slower.

Add the rest of it:

| | |
|---|---|
| Licence | Apple permits virtualising 10.7 **on Apple hardware**, which this is. So this part is fine. |
| Graphics | 10.7 has no driver for the virtual display QEMU offers. Expect a working desktop to be real work, if at all. |
| Memory | 7 GB total. Giving a guest a usable share leaves little for the host. |
| Speed | No EPT, and a 2006 CPU underneath. Slower than the bare-metal Lion you already have. |

**The recommendation:** do not. You already have Lion, running properly on real
hardware, one restart away. A virtual machine would be slower and more fragile
than the thing it replaces. If the goal is reaching *files*, mount the disk
read-only as above — that gets you what you actually wanted, instantly.

The reverse — Linux as a guest inside Lion — is worse still: Lion's era of
VirtualBox and VMware are long unsupported, and the Linux install here is on
bare metal rather than in a disk image.

## Which side to use for what

| | |
|---|---|
| **Linux** | Everything current: the AI tools, the browser, the editor, LibreOffice, video, containers, anything needing the internet. This is where to live. |
| **Lion** | Old Mac software that only exists for Mac OS X, and reaching the previous owner's files in their original environment. |

Lion is genuinely unsafe to browse the web on — it stopped receiving security
updates around 2014, and no current browser supports it. Use Linux for anything
that touches the internet.

## Choosing at boot

The boot menu appears at power-on. If you miss it, restart. Details, including
what to do about a black screen, are in
[LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md).

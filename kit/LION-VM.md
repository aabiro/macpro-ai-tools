# Running Lion as a virtual machine

Mac OS X Lion 10.7.5 boots as a guest while Debian is the live system. This
gives a root shell in Lion from a Linux terminal, which is what makes it
possible for an AI assistant — or anyone working over SSH — to read, change and
*execute* things in Lion. Lion itself is far too old to run modern tooling, so
the tooling stays on the Linux side and reaches in.

For the plain-language version, see
[USING-BOTH-SYSTEMS.md](USING-BOTH-SYSTEMS.md). This file is the technical
record: how it works, why each piece is the way it is, and how to rebuild it.

## Quick start

```
lion-vm start          # headless, ready in about 60 seconds
lion-vm wait           # blocks until sshd answers
lion sw_vers           # run anything inside Lion, as root
lion                   # interactive shell
lion-vm stop           # clean shutdown, about 12 seconds
lion-vm status
```

## The disk is never written, and that is the whole design

The Lion disk is failing: 255 reallocated sectors, 4 currently pending. It must
be spun up as little as possible and written to never.

```
/dev/sdb  (physical, FAILING)  ──backing file, READ-ONLY──┐
                                                          ├─→ guest sees one disk
/var/lib/lion-vm/lion-overlay.qcow2  (copy-on-write) ─────┘
```

QEMU opens `/dev/sdb` read-only. Every guest write — including Lion's own
journal replay and the `fsck` repairs it performs on each boot — goes into the
overlay. Nothing the guest does can reach the physical disk.

Verify it rather than trusting it:

```bash
# The volume header on the physical disk should never change from 0x80002000.
sudo python3 -c "
import struct
f=open('/dev/sdb','rb'); f.seek(409640*512+1024); h=f.read(8)
sig,ver,attr=struct.unpack('>2sHI',h)
print(sig.decode(), ver, hex(attr))"

sudo smartctl -A /dev/sdb | grep -E 'Reallocated_Sector_Ct|Current_Pending'
```

Across a dozen full boots, journal replays and two `fsck` runs that repaired 13
orphaned files and 21 directories, the physical header stayed `0x80002000` and
the SMART counters did not move. All of it landed in the overlay.

**Consequence:** you cannot damage Lion by experimenting in the VM. Break it,
then `lion-vm restore`.

## The five problems that had to be solved

Worth recording, because every one of them fails in a way that looks like
something else, and none of them can be skipped.

### 1. Apple's `boot.efi` is a fat container, and UEFI cannot start it

`boot.efi` begins with magic `0x0EF1FAB9` — an Apple EFI fat container holding
an i386 slice and an x86_64 slice. UEFI `LoadImage` sees no PE header and
refuses it. OpenCore has its own Apple-aware image loader, which is how it
boots real Macs, so entries launched *through OpenCore* work.

Two notes for anyone re-deriving this.

The fat header is **little-endian**. Parsing it big-endian yields nonsense — a
slice count in the tens of millions.

And the HFS+ driver matters: Acidanthera's `HfsPlus.efi` executes `RDRAND`,
which this 2006 Xeon does not implement (`grep rdrand /proc/cpuinfo` returns
nothing), so it faults before it can read the volume — as a hang, not an error
message. **Use `OpenHfsPlus.efi` instead**, the open-source driver from the same
release; it has no such dependency. The working `UEFI/Drivers` list is exactly:

```
OpenRuntime.efi, OpenHfsPlus.efi, OpenUsbKbDxe.efi, Ps2KeyboardDxe.efi
```

### 2. `Could not open file 'mach_kernel'` — the loader's volume matters

`boot.efi` resolves `mach_kernel` and the kext cache **relative to whatever
volume it was loaded from.** Launching a copy from the EFI System Partition
therefore looks for the kernel on a 200 MB FAT partition and fails with error
`0xe` (`EFI_NOT_FOUND`).

`boot-uuid=` does not redirect this. Neither does copying the kernel onto the
ESP — `boot.efi` then finds it but reports the root device as the ESP and dies
at `Error loading drivers`, because `/System/Library/Extensions` is not there.

**The fix is to launch `boot.efi` from the HFS+ volume itself**, via an
OpenCore entry whose device path names partition 2:

```
PciRoot(0x0)/Pci(0x1F,0x2)/Sata(0x1,0xFFFF,0x0)/
HD(2,GPT,258C69C7-A1E1-47CD-B7F5-E403F32E4E86,0x64028,0x74662D60)/
System\Library\CoreServices\boot.efi
```

### 3. `Error allocating 0xe2 pages at 0x800000 alloc type 2`

`alloc type 2` is UEFI `AllocateAddress`: `boot.efi` is demanding the kernel's
fixed load address at 8 MB, and the firmware already owns that region. No boot
argument fixes this — `slide=0` makes it *worse*, because it forces the very
fixed allocation that is failing.

The fix is `Booter/Quirks/AllowRelocationBlock = true`, which allocates a
scratch block in low memory and loads the kernel there instead. It needs
`ProvideCustomSlide` and `AvoidRuntimeDefrag` alongside it.

### 4. Boot arguments must go in NVRAM, not in the OpenCore entry

An entry's `Arguments` string does reach the kernel for some flags — `-x` is
honoured that way, verifiably, since the login window renders "Safe Boot" in
red. But `-s` is silently ignored.

Single-user mode only works when `boot-args` is set as an **NVRAM variable**
under Apple's GUID `7C436110-AB2A-4BBB-A880-FE41995C9F82`, with `WriteFlash`
true and a `Delete` entry alongside the `Add` so an existing value cannot win.
`lion-vm` does this for you; the code is `~/oc/nvram.py`.

### 5. One CPU, and an SMC, or nothing boots

`-device isa-applesmc` with the OSK is mandatory; macOS refuses to boot without
the SMC present. `-smp 1` is also required — with two vCPUs the boot hangs after
`launchd` with zero disk I/O.

`-cpu host` is deliberate. A named model such as `Penryn` would advertise SSE4.1,
which this Xeon does not have and KVM cannot provide. The host CPU is literally
what Lion shipped on, so it is the best possible model.

## What does not work

| | |
|---|---|
| No graphics in a normal boot | 10.7 has no driver for the virtual display. The screen is black while the OS runs perfectly underneath. `lion-vm screenshot` reports `lit=0.00%` — expected, not a fault. |
| Graphics only in safe mode | `lion-vm start --safe` draws the login window; VNC to `127.0.0.1:5901`. Safe mode disables a lot, so it is for looking, not working. |
| No EPT | These Xeons predate nested paging, so KVM emulates memory management in software. Fine for shell work. |
| `-s` from the picker | Holding Cmd-S is not available; use `lion-vm start --single`. |

## Files

| Path | What it is |
|---|---|
| `/usr/local/bin/lion-vm` | Start, stop, snapshot, restore, screenshot |
| `/usr/local/bin/lion` | Run a command inside Lion over SSH |
| `~/oc/run-lion.sh` | The QEMU invocation |
| `~/oc/rebuild.sh` | Rebuilds the OpenCore FAT image from `~/oc/esp/` |
| `~/oc/nvram.py` | Sets `boot-args` in the OpenCore config's NVRAM section |
| `~/oc/mon.py` | Talks to the QEMU monitor socket |
| `~/oc/type.py` | Types a string into the guest console via `sendkey` |
| `~/.ssh/lion_vm_key` | RSA key for the VM. Generated on this machine, stays here |
| `/var/lib/lion-vm/lion-overlay.qcow2` | All guest writes |
| `/var/lib/lion-vm/lion-overlay.qcow2.provisioned` | Snapshot with SSH working |

Copies of every script above, plus the working `opencore-config.plist`, are
kept in this repo at `kit/macos-lion/vm/` — the machine's home directory is
not the only copy. `OpenHfsPlus.efi` and `OpenRuntime.efi` are not committed;
they come from an OpenCore release and `build-oc.py` fetches them.

## Re-provisioning after `lion-vm reset`

SSH access lives in the overlay. `lion-vm reset` returns to the bare disk and
therefore removes it — the real Lion install has Remote Login off. `lion-vm
restore` is nearly always what you want instead.

If you do need to set it up again from scratch:

1. Stage the files on the overlay's FAT ESP from Linux (writing FAT from Linux
   is safe; writing HFS+ from Linux is **not** — it corrupted an overlay once,
   which is why this route exists at all):

   ```bash
   sudo modprobe nbd max_part=8
   sudo qemu-nbd --connect=/dev/nbd1 /var/lib/lion-vm/lion-overlay.qcow2
   sudo mount -t vfat -o rw /dev/nbd1p1 /mnt/ovlesp
   sudo cp kit/macos-lion/setup-lion-ssh.sh /mnt/ovlesp/setup.sh
   sudo cp ~/.ssh/lion_vm_key.pub /mnt/ovlesp/lion_key.pub
   sudo umount /mnt/ovlesp && sudo qemu-nbd --disconnect /dev/nbd1
   ```

2. Boot to a root shell — no password involved, single-user mode does not use
   one:

   ```bash
   lion-vm start --single
   lion-vm screenshot        # confirm the ":/ root#" prompt
   ```

3. Type into the guest console. Check the device node first: the guest's disk
   numbering **is not stable** between boots — the Lion volume has appeared as
   both `disk0s2` and `disk1s2` depending on which disk enumerated first.

   ```bash
   python3 ~/oc/type.py '/sbin/mount -uw /
   '
   python3 ~/oc/type.py 'ls -d /dev/disk0s1 /dev/disk1s1
   '
   lion-vm screenshot        # see which one exists
   python3 ~/oc/type.py 'mkdir -p /m
   '
   python3 ~/oc/type.py '/sbin/mount_msdos /dev/disk1s1 /m
   '
   python3 ~/oc/type.py 'sh /m/setup.sh
   '
   ```

4. The script logs to `/m/setup.log`, on the FAT partition, so read it back
   from Linux to confirm rather than squinting at a screenshot.

5. Restart normally and snapshot:

   ```bash
   lion-vm stop && lion-vm start && lion-vm wait && lion sw_vers
   lion-vm snapshot
   ```

## Diagnostics

```bash
lion-vm status                      # running? overlay size? last serial lines?
tail -40 ~/oc/serial.log            # OpenCore and boot.efi talk here
lion-vm screenshot /tmp/s.png       # the kernel talks here, not to serial
python3 ~/oc/mon.py "info blockstats"   # rd_bytes climbing = still working
```

Two traps worth knowing:

- **Port 2222 accepting a connection proves nothing.** QEMU's user-mode
  forwarding accepts on the host side even when nothing is listening in the
  guest. Test with `lion true`, not with a port check.
- **`no matching host key type found` does not mean sshd is down.** Lion ships
  OpenSSH 5.x, whose RSA-SHA1 host keys a modern client rejects by default. The
  `lion` wrapper passes `HostKeyAlgorithms=+ssh-rsa` and
  `PubkeyAcceptedAlgorithms=+ssh-rsa` for exactly this reason. If you connect
  by hand, you need them too.

The forward is bound to `127.0.0.1:2222` deliberately. `tcp::2222` would put
the guest's sshd on the LAN, where it has no business being.

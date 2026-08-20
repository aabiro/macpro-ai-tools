# Disk health, and the fact that there is no backup

Read this before putting anything important on this machine.

Measured on 2026-08-19 with `smartctl`. These are the real values, not estimates.

---

## The two drives

| | `/dev/sda` — Debian | `/dev/sdb` — Mac OS X Lion |
|---|---|---|
| Model | ST31000333AS | SAMSUNG HD103SI |
| Capacity | 1.00 TB | 1.00 TB |
| SMART verdict | PASSED | PASSED |
| Power-on hours | 20,274 (2.3 years) | 20,870 (2.4 years) |
| Reallocated sectors | **8** | **255** |
| Reallocated events | — | **255** |
| Reported uncorrectable | 0 | **2,814** |
| Current pending sectors | 0 | 0 |
| Spin retry count | 0 | 1 |
| Cable errors (UDMA CRC) | 0 | 0 |

## What those numbers mean

**Reallocated sectors.** The disk surface is divided into sectors. When one fails,
the drive swaps in a spare from a reserve pool and remaps it, silently. The count
is a tally of how many times the drive has patched around physical damage. `sda`'s
8 is unremarkable for a drive this age. `sdb`'s 255 is a lot.

**255 probably means "255 or more."** Both counters on `sdb` read exactly 255,
which is the ceiling of an 8-bit field. When two independent counters saturate at
the same round number, the real figure is likely higher and simply cannot be
represented in the attribute.

**Reported_Uncorrect: 2,814 — this is the number that matters most.** It counts
occasions the drive told the operating system *"I cannot read that data."* Not
remapped, not recovered: failed. Nearly three thousand times.

**Why it still says PASSED.** `Current_Pending_Sector` is 0, meaning there is no
sector currently waiting to be dealt with, and the normalised values are above
their failure thresholds (91 against a threshold of 10). SMART's pass/fail is a
narrow question and this drive passes it. It is not a statement that the drive is
healthy.

**Cable errors are 0 on both**, which rules out the SATA cabling as a cause and
points the finger squarely at the `sdb` platter surface.

## There is no backup. This is the important part.

An earlier stage of this project kept a bootable clone of Lion in a second
volume called `Liferaft`. **It no longer exists.** When `disk0` was consolidated
into a single full-size volume, that clone was absorbed. Only one HFS+ volume
remains:

```
$ lsblk -o NAME,SIZE,FSTYPE,LABEL
sdb
├─sdb1   200M vfat     EFI
└─sdb2 931.2G hfsplus  Lion      <- the only copy of this data
```

It is worth being blunt: even while `Liferaft` existed it was on the **same
physical disk** as the original, so it was never protection against that disk
failing. It guarded against a bad OS upgrade, nothing more.

So roughly 233 GB of the previous owner's files sit on the drive with 2,814
uncorrectable reads, with no copy anywhere.

## What to do about it

**First, and before anything else: copy that data off the machine.** An external
USB drive is the simplest route. From Linux the Lion volume can be mounted
read-only, which is the safest way to read from a suspect disk:

```bash
sudo mkdir -p /mnt/lion
sudo mount -o ro /dev/sdb2 /mnt/lion
# then copy /mnt/lion/Users/... to external storage
```

Use `rsync` rather than a file manager, so an unreadable file logs an error and
the copy carries on instead of aborting:

```bash
rsync -a --info=progress2 /mnt/lion/Users/ /media/your-external-drive/lion-backup/
```

Expect some files to fail. Those are the 2,814 events, made visible. Note which
ones, so you know what was lost rather than discovering it years later.

**Then set up ongoing backups** — step 5 of
[FIRST-RUN-CHECKLIST.md](FIRST-RUN-CHECKLIST.md).

**Do not reformat or reinstall over `sdb2` until that copy exists.**

## Should the drive be replaced?

Probably, and it is cheap and easy: a 3.5" SATA drive in a tray, and this model
takes four of them. But the order matters — **copy the data first, replace
second.** A drive with this history can deteriorate quickly, and the worst
outcome is losing the data while trying to improve the hardware.

`sda`, which holds Debian, is in good shape. If `sdb` is replaced, everything
described in [AI-STACK.md](AI-STACK.md) keeps working untouched, because none of
it lives there.

## Keeping an eye on it

The machine collects these numbers every five minutes:

```bash
macpro-telemetry | grep -A12 smart
```

Or open the cockpit's **Status** tab, which shows all of it with non-zero
counters highlighted. Watch two things:

- **`Current_Pending_Sector` rising above 0** — that means a sector is failing
  *right now*, and is the signal to stop using the drive.
- **`Reported_Uncorrect` climbing** from 2,814.

If either moves, act rather than wait.

# Disk health, and the fact that there is no backup

Read this before putting anything important on this machine.

Measured on 2026-08-19 with `smartctl`. These are the real values, not estimates.

---

## The two drives

| | **Debian drive** | **Lion drive** |
|---|---|---|
| Model | ST31000333AS | SAMSUNG HD103SI |
| Identify it by | ext4, mounted at `/` | hfsplus, label `Lion` |
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
is a tally of how many times the drive has patched around physical damage. The
Debian drive's 8 is unremarkable for its age. The Lion drive's 255 is a lot.

**255 probably means "255 or more."** Both counters on the Lion drive read exactly 255,
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
points the finger squarely at the Lion drive's platter surface.

## There is no backup. This is the important part.

An earlier stage of this project kept a bootable clone of Lion in a second
volume called `Liferaft`. **It no longer exists.** When `disk0` was consolidated
into a single full-size volume, that clone was absorbed. Only one HFS+ volume
remains:

```
$ lsblk -o NAME,SIZE,FSTYPE,LABEL
sda                                        <- letter varies between boots
├─sda1   200M vfat     EFI
└─sda2 931.2G hfsplus  Lion                <- the only copy of this data
```

It is worth being blunt: even while `Liferaft` existed it was on the **same
physical disk** as the original, so it was never protection against that disk
failing. It guarded against a bad OS upgrade, nothing more.

So roughly 233 GB of the previous owner's files sit on the drive with 2,814
uncorrectable reads, with no copy anywhere.

## What to do about it

**First, and before anything else: copy that data off the machine.**

> ### Device names are NOT stable on this machine
>
> `sda` and `sdb` **swap between boots.** They were Debian=sda / Lion=sdb, and
> after a hardware reseat they became Lion=sda / Debian=sdb. Earlier versions of
> these docs hardcoded `/dev/sdb2` for Lion, which after that swap pointed at
> Debian's root filesystem instead. On a worn disk holding the only copy of
> someone's files, that class of instruction destroys data.
>
> **Always identify the disk by label or filesystem, never by letter:**
>
> ```bash
> lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT   # look, every time
> ```
>
> Lion is the **hfsplus** partition labelled **Lion**. Debian is the **ext4**
> one mounted at **/**.

Mount it read-only, by label, which is safe whichever letter it has today.
Lion's journal is dirty, so `force` is required — this stays read-only:

```bash
sudo mkdir -p /mnt/lion
sudo mount -t hfsplus -o ro,force /dev/disk/by-label/Lion /mnt/lion
df -h /mnt/lion            # confirm you got a ~932G volume before copying
```

Use `rsync` rather than a file manager, so an unreadable file logs an error and
the copy carries on instead of aborting:

```bash
rsync -a --info=progress2 /mnt/lion/Users/ /media/your-external-drive/lion-backup/
```

Expect some files to fail. Those are the 2,814 events, made visible. Note which
ones, so you know what was lost rather than discovering it years later.

### Where to copy it to

**An external USB drive is the best answer**, and the one to reach for first:

```bash
lsblk                                    # find the drive you just plugged in
sudo mkdir -p /mnt/ext
sudo mount /dev/disk/by-label/YOURDRIVE /mnt/ext
sudo rsync -a --info=progress2 --partial --append-verify --ignore-errors \
     /mnt/lion/Users/ /mnt/ext/lion-backup/Users/
```

`--ignore-errors` matters here: with 2,814 recorded read failures, some files
**will** be unreadable. Without it one bad file aborts the whole copy. With it,
the copy continues and names the failures in its output — note them, so you know
what was lost rather than discovering it in five years.

`--partial --append-verify` makes it resumable, so an interrupted run continues
rather than starting again.

**Over the network to another computer** works too, same flags:

```bash
rsync -a --info=progress2 --partial --append-verify --ignore-errors \
     /mnt/lion/Users/ user@other-machine:/path/lion-backup/Users/
```

Expect roughly **25 MB/s**, so about 2.5 hours for 233 GB. That is the limit of
a worn 2009 drive in a 2006 machine, not the network.

### Cloud backup: what it actually costs

Offered as an option, not a requirement. **You do not need it to use this
machine safely** — an external drive is enough.

If you want offsite copies, Backblaze B2 is the cheapest sensible choice:

| | |
|---|---|
| First 10 GB | free |
| Storage after that | about **$6 per TB per month** |
| So 233 GB | roughly **$1.40 a month** |
| Downloading it back | free up to 3x your stored amount |

It needs an account with a card on file. `restic` is the tool that talks to it:

```bash
sudo apt install restic
```

Full setup is in [FIRST-RUN-CHECKLIST.md](FIRST-RUN-CHECKLIST.md) step 5. If you
would rather not have a subscription, use the external drive and skip this
entirely — that is a perfectly good answer.

**Do not reformat or reinstall over the Lion volume until that copy exists.**

## Should the drive be replaced?

Probably, and it is cheap and easy: a 3.5" SATA drive in a tray, and this model
takes four of them. But the order matters — **copy the data first, replace
second.** A drive with this history can deteriorate quickly, and the worst
outcome is losing the data while trying to improve the hardware.

The Debian drive is in good shape. If the Lion drive is replaced, everything
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

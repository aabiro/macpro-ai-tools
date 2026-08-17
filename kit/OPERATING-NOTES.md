# Operating Notes — driving this Mac over SSH/MCP

Practical findings from doing real work on this machine remotely, as the
non-interactive `ai-cockpit` account. Written down because most of it is
non-obvious and cost time to discover.

The headline: **a lot of apparently privileged work needs no password at all.**
Reach for sudo last, not first.

---

## 1. The privilege situation

```
account        : ai-cockpit
groups         : staff, admin          <- in admin
sudo -n true   : "a password is required to run sudo"
console owner  : administrator
```

Being in `admin` **permits** sudo; it does not waive the password. Over SSH with
no TTY there is no way to supply one, so anything genuinely requiring root is
out of reach and has to be handed to a human.

But group membership is not useless — see §2.

## 2. What works WITHOUT sudo

This is the important part. `admin` group membership grants write access to
directories owned by `root:admin` with group-write set:

```
$ ls -ld /Applications
drwxrwxr-x+ root admin /Applications      <- group-writable
```

So an application can be installed by writing the bundle directly, with no
`installer` invocation and no password.

Worked example — installing Apple's El Capitan installer app, which normally
means `sudo installer -pkg ... -target /`:

```bash
# 1. list what the pkg would install (no privileges)
pkgutil --payload-files "/Volumes/Install OS X/InstallMacOSX.pkg"

# 2. pull just the small app-shell payload out of the flat pkg
xar -xf "$PKG" InstallMacOSX.pkg/Payload
gunzip -c Payload | cpio -idmu           # yields the .app

# 3. place it (works because /Applications is group-writable)
ditto "Install OS X El Capitan.app" "/Applications/Install OS X El Capitan.app"

# 4. the big OS image lives inside the bundle
ditto InstallESD.dmg "/Applications/.../Contents/SharedSupport/InstallESD.dmg"
```

Result: a complete, valid 5.8 GB installer, assembled with zero privileges.

Unprivileged and useful: `pkgutil`, `xar`, `cpio`, `ditto`, `hdiutil attach`,
`diskutil list`/`info`, `system_profiler`, `ioreg`, `sysctl`, `vm_stat`, `df`,
`bless --info` (reading), `mdutil` (reading state).

## 3. What genuinely needs a password

Hand these to a human. Confirmed by attempting them:

| Command | Error |
|---|---|
| `shutdown -h now` | `shutdown: NOT super-user` |
| `halt` | `Operation not permitted` |
| `diskutil resizeVolume` | `Insufficient privileges (-69863)` |
| `diskutil appleRAID delete` | needs auth |
| `diskutil verifyVolume` | `-69863` |
| `mdutil -i off` | `Try as root. (-1)` |
| `pmset -a sleep 0` | `must be run as root` |
| `installer -pkg -target /` | needs root |
| `bless --setBoot` | needs root |

Note `diskutil resizeVolume` reports only **"Error resizing volume"** — the real
`-69863` privilege error only surfaces from `verifyVolume`. Don't waste time
hunting a filesystem fault that isn't there.

## 4. GUI is unreachable, and root would not help

The apps belong to `administrator`'s Aqua session:

```
osascript ... 'tell application "loginwindow"'  -> error -10810
osascript ... 'tell application "Microsoft Word" to quit'  -> silent no-op
```

Error `-10810` means no reachable session. This is a **session** boundary, not a
privilege one — root would not fix it either. And forcing a quit on an app with
an unsaved document risks destroying it: macOS would put a save dialog on the
console user's screen and cancel the operation.

Anything GUI-only (MacPostFactor, Disk Utility's Restore tab) must be driven by
a person at the keyboard.

## 5. Long-running jobs vs. the MCP timeout

The MCP call times out well before a multi-GB operation finishes, and the SSH
session closing takes the shell with it. Pattern that works:

```bash
cat > /tmp/job.sh <<'EOF'
#!/bin/bash
exec > /tmp/job.log 2>&1     # log everything; the caller reads this later
...work...
echo "DONE $(date)"          # explicit completion marker
EOF
chmod +x /tmp/job.sh
nohup /tmp/job.sh >/dev/null 2>&1 </dev/null &
disown
```

Then poll `/tmp/job.log` from later calls, gating on the `DONE` marker.

Three traps, all of which bit:

- **`setsid` does not exist on macOS.** It is a Linux util-linux tool. Using it
  makes the launch fail with exit 1 and no log. Use `nohup ... & disown`.
- **`pgrep -f <script>` is unreliable here.** It reported a job finished that
  was still running, and matched its own command line at other times. *Gate on a
  marker written to the log, never on process presence.* This caused a real
  defect: a wait loop exited early and `ditto` copied a still-being-written
  6 GB file, silently producing a 538 MB-short truncated result.
- **`ditto` writes to a temp file then renames.** Mid-copy the destination name
  does not exist; progress shows up as `.BC.XXXXXX` in the target directory.

## 6. Always verify a large copy by size, then by structure

The truncated-DMG bug above passed every casual check. What caught it:

```bash
[ "$(stat -f %z "$SRC")" = "$(stat -f %z "$DST")" ] || echo MISMATCH
hdiutil imageinfo "$DST" | grep -i "Checksum Type"
```

A valid compressed DMG reports `Checksum Type: CRC32`. The truncated copy
reported `Format: UDRW` and `Checksum Type: none`. Size plus format together are
a reliable check; either alone is not.

## 7. Connecting from a modern machine

Modern OpenSSH refuses Lion's key algorithms by default:

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    user@<host>
```

Without these: `no matching host key type found. Their offer: ssh-rsa,ssh-dss`.
That is a policy mismatch, not a fault on either side.

## 8. Spotlight blocks unmounts

`diskutil unmount` failing on a secondary volume is almost always `mds`
indexing it. `mdutil -i off <volume>` (needs root) then a force unmount clears
it. Diagnose with `mdutil -s <volume>` — "Indexing enabled" is the tell.

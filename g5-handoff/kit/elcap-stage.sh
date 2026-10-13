#!/bin/bash
#
# elcap-stage.sh -- do every privileged step of the El Capitan preparation in
# one run, so it costs a single sudo prompt instead of a dozen round trips.
#
#     sudo /Users/Shared/elcap-stage.sh
#
# It is idempotent: re-running skips anything already done. It never touches
# Lion, Liferaft, or the El Capitan install target -- only the Installer volume
# and /Applications.
#
set -uo pipefail

DMG_ELCAP="/Users/Shared/InstallMacOSX.dmg"
DMG_MPF="/Users/Shared/MacPostFactor_2.0.dmg"
APP="/Applications/Install OS X El Capitan.app"
TARGET="/Volumes/Installer"

ok()   { printf '  [ok]   %s\n' "$*"; }
skip() { printf '  [--]   %s\n' "$*"; }
bad()  { printf '  [!!]   %s\n' "$*" >&2; }
step() { printf '\n==> %s\n' "$*"; }

if [ "$(id -u)" != "0" ]; then
    echo "Run me with sudo:" >&2
    echo "    sudo $0" >&2
    exit 1
fi

# --------------------------------------------------------------------------
step "Safety check -- confirm the disks are what we think"
# --------------------------------------------------------------------------
BOOT=$(df / | tail -1 | awk '{print $1}')
echo "  booted from : $BOOT  ($(diskutil info / 2>/dev/null | awk -F': *' '/Volume Name/{print $2}'))"
for d in disk0s2 disk0s3 disk0s4 disk1s2; do
    n=$(diskutil info $d 2>/dev/null | awk -F': *' '/Volume Name/{print $2}')
    s=$(diskutil info $d 2>/dev/null | awk -F': *' '/Total Size/{print $2}' | sed 's/ (.*//')
    [ -n "$n" ] && printf "  %-9s %-14s %s\n" "$d" "$n" "$s"
done

if [ "$BOOT" != "/dev/disk0s3" ]; then
    bad "Expected to be booted from /dev/disk0s3 (Lion). Got $BOOT."
    bad "Stopping -- verify where you are before continuing."
    exit 1
fi
ok "booted from the restored Lion"

# --------------------------------------------------------------------------
step "Mount the disk images"
# --------------------------------------------------------------------------
for img in "$DMG_ELCAP" "$DMG_MPF"; do
    [ -f "$img" ] || { bad "missing: $img"; exit 1; }
done

if [ ! -f "/Volumes/Install OS X/InstallMacOSX.pkg" ]; then
    hdiutil attach "$DMG_ELCAP" -nobrowse -quiet && ok "mounted El Capitan image" \
        || { bad "could not mount $DMG_ELCAP"; exit 1; }
else
    skip "El Capitan image already mounted"
fi

if [ ! -d "/Volumes/MacPostFactor v2.0/MacPostFactor.app" ]; then
    hdiutil attach "$DMG_MPF" -nobrowse -quiet && ok "mounted MacPostFactor" \
        || bad "could not mount $DMG_MPF"
else
    skip "MacPostFactor already mounted"
fi

# --------------------------------------------------------------------------
step "Install the El Capitan installer app into /Applications"
# --------------------------------------------------------------------------
# MacPostFactor requires the .app to be in /Applications. The pkg inside
# Apple's DMG is what puts it there. ~6 GB, a few minutes on this hardware.
if [ -d "$APP" ]; then
    skip "already present: $APP"
else
    PKG="/Volumes/Install OS X/InstallMacOSX.pkg"
    [ -f "$PKG" ] || { bad "pkg not found at $PKG"; exit 1; }
    echo "  running Apple's installer (several minutes, ~6 GB) ..."
    if installer -pkg "$PKG" -target / ; then
        ok "installed"
    else
        bad "installer failed"
        exit 1
    fi
fi

if [ -d "$APP" ]; then
    ok "verified: $APP ($(du -sh "$APP" 2>/dev/null | cut -f1))"
else
    bad "the app did not land in /Applications -- cannot continue"
    exit 1
fi

# --------------------------------------------------------------------------
step "Prepare the Installer volume"
# --------------------------------------------------------------------------
if [ ! -d "$TARGET" ]; then
    bad "$TARGET is not mounted. Expected the 24.7 GB Installer partition."
    exit 1
fi
SZ=$(df -h "$TARGET" | tail -1 | awk '{print $2}')
ok "target ready: $TARGET ($SZ)"

# Spotlight on the target competes with the patcher for the disk and has caused
# the unmount failures we already hit once tonight on Macintosh RAID.
mdutil -i off "$TARGET" >/dev/null 2>&1 && ok "Spotlight indexing disabled on the target" \
    || skip "could not change Spotlight state (harmless)"

# --------------------------------------------------------------------------
step "Keep the machine awake"
# --------------------------------------------------------------------------
pmset -a sleep 0 disksleep 0 >/dev/null 2>&1 && ok "system and disk sleep disabled" \
    || skip "could not change power settings"

# --------------------------------------------------------------------------
step "Ready"
# --------------------------------------------------------------------------
cat <<EOF

  Everything privileged is done. What remains is one GUI step that has to be
  driven by hand -- MacPostFactor has no command-line interface.

  Launch it:

      open "/Volumes/MacPostFactor v2.0/MacPostFactor.app"

  In its window choose:

      OS version    : El Capitan (10.11)
      Installer app : /Applications/Install OS X El Capitan.app
      Destination   : Installer          <-- the 24.7 GB volume

  DO NOT pick any of these as the destination:

      Lion          825.0 GB   your working system
      Liferaft      999.9 GB   your backup
      El Capitan    149.9 GB   the install TARGET, not the installer media

  Read the size before you click. Four HFS+ volumes are mounted.

  When it finishes: restart holding Option and choose "Installer".
  Being an internal partition, it boots far more reliably here than USB.

EOF

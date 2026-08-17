#!/bin/bash
#
# build-elcap-media.sh -- build bootable El Capitan install media by hand,
# on the Installer partition, for a Mac with 32-bit EFI.
#
#     sudo /Users/Shared/build-elcap-media.sh
#
# This replaces MacPostFactor, whose download backend went offline around 2016
# ("URL uninitialized / check internet connection" is that server being gone,
# not a local fault). MacPostFactor was only ever automating the six steps
# below; the one that matters is swapping in Piker-Alpha's 32-bit boot.efi,
# which we now have directly and checksum-verified.
#
# SAFETY: writes to /Volumes/Installer and nowhere else. It refuses to run if
# the target is not the expected ~23 GiB partition, and it never touches Lion,
# Liferaft, or the El Capitan install target.
#
set -uo pipefail

TARGET="/Volumes/Installer"
TARGET_DEV="disk0s4"
APP="/Applications/Install OS X El Capitan.app"
ESD="$APP/Contents/SharedSupport/InstallESD.dmg"
PATCHED_EFI="/Users/Shared/boot_grey.efi"
EXPECT_EFI_SHA1="41ec2b9ac115cb6def687b1bfdef891df6556b74"
ESD_MNT="/tmp/elcap-esd"

ok()   { printf '  [ok]   %s\n' "$*"; }
bad()  { printf '  [!!]   %s\n' "$*" >&2; }
step() { printf '\n==> %s\n' "$*"; }
die()  { bad "$*"; bad "STOPPING - nothing further was changed."; cleanup; exit 1; }

cleanup() {
    hdiutil detach "$ESD_MNT" -quiet 2>/dev/null
    rmdir "$ESD_MNT" 2>/dev/null
}
trap cleanup EXIT

[ "$(id -u)" = "0" ] || { echo "Run with sudo: sudo $0" >&2; exit 1; }

# --------------------------------------------------------------------------
step "0. Safety checks"
# --------------------------------------------------------------------------
BOOTVOL=$(df / | tail -1 | awk '{print $1}')
[ "$BOOTVOL" = "/dev/disk0s3" ] || die "Expected to be booted from /dev/disk0s3 (Lion), got $BOOTVOL"
ok "booted from Lion ($BOOTVOL) - not the target"

[ -d "$TARGET" ] || die "$TARGET is not mounted"
TDEV=$(diskutil info "$TARGET" 2>/dev/null | awk -F': *' '/Device Node/{print $2}')
[ "$TDEV" = "/dev/$TARGET_DEV" ] || die "$TARGET is $TDEV, expected /dev/$TARGET_DEV. Refusing to write to an unexpected disk."
TSIZE=$(df -g "$TARGET" | tail -1 | awk '{print $2}')
[ "$TSIZE" -ge 15 ] && [ "$TSIZE" -le 40 ] || die "$TARGET is ${TSIZE}Gi; expected roughly 23Gi. Refusing - this may be the wrong volume."
ok "target verified: $TARGET on $TDEV (${TSIZE}Gi)"

[ -f "$ESD" ] || die "InstallESD.dmg not found at $ESD"
ok "installer image present ($(stat -f %z "$ESD") bytes)"

[ -f "$PATCHED_EFI" ] || die "Patched bootloader missing: $PATCHED_EFI"
GOT=$(shasum -a 1 "$PATCHED_EFI" | awk '{print $1}')
[ "$GOT" = "$EXPECT_EFI_SHA1" ] || die "boot_grey.efi checksum mismatch. Got $GOT, expected $EXPECT_EFI_SHA1. Refusing to install an unverified bootloader."
ok "patched bootloader verified (sha1 $GOT)"

# --------------------------------------------------------------------------
step "1. Mount the installer image"
# --------------------------------------------------------------------------
cleanup
mkdir -p "$ESD_MNT"
hdiutil attach "$ESD" -nobrowse -readonly -noverify -mountpoint "$ESD_MNT" >/dev/null 2>&1 \
    || die "could not mount $ESD (is it already mounted? check /Volumes)"
[ -f "$ESD_MNT/BaseSystem.dmg" ] || die "BaseSystem.dmg not inside the image - the installer app is incomplete"
ok "mounted; BaseSystem.dmg is $(stat -f %z "$ESD_MNT/BaseSystem.dmg") bytes"
[ -d "$ESD_MNT/Packages" ] || die "Packages folder missing from the image"
ok "Packages folder present ($(du -sm "$ESD_MNT/Packages" | cut -f1) MB)"

# --------------------------------------------------------------------------
step "2. Restore BaseSystem onto the target (makes it bootable)"
# --------------------------------------------------------------------------
# BaseSystem.dmg is itself a small bootable OS X containing the installer app.
# asr can block-copy it because the SOURCE here is a read-only image -- which is
# exactly why restoring Lion earlier failed and needed ditto instead.
echo "  this takes several minutes ..."
asr restore --source "$ESD_MNT/BaseSystem.dmg" --target "$TARGET" --erase --noprompt \
    >/dev/null 2>&1 || die "asr restore failed"
# asr renames the volume to the source's name.
sleep 3
NEWVOL=$(diskutil info "/dev/$TARGET_DEV" 2>/dev/null | awk -F': *' '/Mount Point/{print $2}')
[ -n "$NEWVOL" ] || die "target did not remount after restore"
ok "restored; volume now mounted at $NEWVOL"

# --------------------------------------------------------------------------
step "3. Replace the Packages symlink with the real folder"
# --------------------------------------------------------------------------
# On a freshly restored BaseSystem this is a symlink pointing back into the ESD.
# Left alone, the result is a net-installer that cannot install offline.
PKGDIR="$NEWVOL/System/Installation/Packages"
rm -f "$PKGDIR" 2>/dev/null
[ -e "$PKGDIR" ] && rm -rf "$PKGDIR"
echo "  copying ~5 GB of packages, this is the slow part ..."
ditto "$ESD_MNT/Packages" "$PKGDIR" || die "copying Packages failed"
ok "Packages installed ($(du -sm "$PKGDIR" | cut -f1) MB)"

# --------------------------------------------------------------------------
step "4. Copy BaseSystem image and chunklist to the volume root"
# --------------------------------------------------------------------------
ditto "$ESD_MNT/BaseSystem.dmg" "$NEWVOL/BaseSystem.dmg" || die "copying BaseSystem.dmg failed"
ditto "$ESD_MNT/BaseSystem.chunklist" "$NEWVOL/BaseSystem.chunklist" 2>/dev/null
SRC_SZ=$(stat -f %z "$ESD_MNT/BaseSystem.dmg")
DST_SZ=$(stat -f %z "$NEWVOL/BaseSystem.dmg")
[ "$SRC_SZ" = "$DST_SZ" ] || die "BaseSystem.dmg copy is short: $DST_SZ vs $SRC_SZ"
ok "BaseSystem.dmg copied and size-verified ($DST_SZ bytes)"

# --------------------------------------------------------------------------
step "5. Install the 32-bit bootloader  <-- the actual patch"
# --------------------------------------------------------------------------
# Stock boot.efi is 64-bit-EFI only and simply will not start on a MacPro1,1.
# Piker-Alpha's 32-bit build is what makes this machine able to boot El Capitan.
CS="$NEWVOL/System/Library/CoreServices"
[ -d "$CS" ] || die "$CS missing - the restore did not produce a system"
[ -f "$CS/boot.efi" ] && cp -p "$CS/boot.efi" "$CS/boot.efi.stock-backup"
cp "$PATCHED_EFI" "$CS/boot.efi" || die "could not install the patched bootloader"
chmod 644 "$CS/boot.efi"
chown root:wheel "$CS/boot.efi" 2>/dev/null
INST=$(shasum -a 1 "$CS/boot.efi" | awk '{print $1}')
[ "$INST" = "$EXPECT_EFI_SHA1" ] || die "installed bootloader does not match: $INST"
ok "32-bit boot.efi installed and verified (stock kept as boot.efi.stock-backup)"

# --------------------------------------------------------------------------
step "6. Bless the volume"
# --------------------------------------------------------------------------
bless --folder "$CS" --bootefi --verbose >/dev/null 2>&1 || bless --folder "$CS" --bootefi
if bless --info "$NEWVOL" 2>&1 | grep -q "Blessed System File is"; then
    ok "blessed - will appear in the Option-key boot picker"
else
    bad "bless did not take; the volume may not appear at boot"
fi

# --------------------------------------------------------------------------
step "Done"
# --------------------------------------------------------------------------
cat <<EOF

  Install media ready on: $NEWVOL
    size used : $(df -h "$NEWVOL" | tail -1 | awk '{print $3}')
    bootloader: 32-bit (Piker-Alpha El Capitan build, grey/legacy)

  Untouched, as intended:
    Lion        $(df -h / | tail -1 | awk '{print $3}') used   your working system
    El Capitan  $(df -h "/Volumes/El Capitan" 2>/dev/null | tail -1 | awk '{print $3}') used   the install TARGET, still empty
    Liferaft    $(df -h /Volumes/Liferaft 2>/dev/null | tail -1 | awk '{print $3}') used   your backup

  NEXT - Boot 4:
    1. Restart, holding Option from before the chime
    2. Choose the restored volume (it will be named after BaseSystem, likely
       "OS X Base System") -- NOT Lion, NOT Liferaft
    3. When the installer loads, choose "El Capitan" (149.9 GB) as the
       destination. Read the SIZE before committing.

  If it does not appear in the picker, the bless did not stick; say so and it
  can be re-blessed without rebuilding any of the above.

EOF

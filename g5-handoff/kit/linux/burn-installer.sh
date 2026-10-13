#!/bin/bash
# burn-installer.sh -- burn the staged Debian installer to a blank DVD.
#
# The ISO is already downloaded and checksum-verified at:
#     /Users/Shared/debian-mac-13.6.0-amd64-netinst.iso
#
# This is the Mac-specific Debian build. It carries a 32-bit EFI bootloader,
# which is what this machine needs -- its firmware reports EFI32, so the
# standard Debian image will not appear in the boot picker at all.
#
# Usage:
#     1. Put a blank DVD-R in the drive
#     2. ./burn-installer.sh
#
set -u

ISO="/Users/Shared/debian-mac-13.6.0-amd64-netinst.iso"
EXPECTED="d25a26e33fc7af4868baae426b30bed902a1d70ce84e1e73e96fc5386a179e33"

if [ ! -f "$ISO" ]; then
    echo "Installer image not found at:"
    echo "    $ISO"
    echo ""
    echo "Re-download it on a modern computer from"
    echo "    https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/"
    echo "and note the debian-mac- prefix -- the standard image will not boot here."
    exit 1
fi

echo "Verifying the image before burning ..."
ACTUAL=$(shasum -a 256 "$ISO" | awk '{print $1}')
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "CHECKSUM MISMATCH -- not burning."
    echo "  expected: $EXPECTED"
    echo "  actual:   $ACTUAL"
    echo "The download is damaged. Fetch it again."
    exit 1
fi
echo "  ok, image is intact."
echo ""

echo "Checking the drive ..."
if drutil status 2>&1 | grep -qi "No Media Inserted"; then
    echo "No disc in the drive. Put a blank DVD-R in and run this again."
    exit 1
fi
drutil status 2>&1 | sed -n '1,8p'
echo ""

printf "Burn this image to the disc? [y/N] "
read -r ANSWER
case "$ANSWER" in
    y|Y|yes|YES) ;;
    *) echo "Not burned."; exit 0 ;;
esac

echo ""
echo "Burning. This takes roughly 10 minutes -- do not eject or sleep the Mac."
hdiutil burn "$ISO"
RC=$?

echo ""
if [ $RC -eq 0 ]; then
    cat <<'DONE'
Burned successfully.

Next:
  1. Restart, holding the Option (Alt) key from the moment you hear the chime
  2. Choose the DVD. It may be labelled "Windows" -- that is the generic icon
     for any non-Apple bootable disc, and is expected
  3. Choose "Install" (the plain text installer is more reliable here)

Full instructions: /Users/Shared/ai-cockpit/docs/LINUX-STARTER-PACK.md

IMPORTANT: at the partitioning step, select the SEAGATE ST31000333AS disk.
The Samsung HD103SI holds your Lion system. Verify by model name, not by
disk number -- numbering can change between boots.
DONE
else
    echo "Burn failed (exit $RC). Common causes: the disc is not blank, it is a"
    echo "DVD+R the drive dislikes, or the drive needs a different disc brand."
fi
exit $RC

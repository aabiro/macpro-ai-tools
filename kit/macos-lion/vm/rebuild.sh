#!/bin/bash
# Rebuild the OpenCore ESP image from the esp/ tree.
# Copies EVERY driver present rather than a hardcoded list -- a stale list
# silently shipped an image missing the drivers that had just been added.
cd "$HOME/oc" || exit 1
export MTOOLS_SKIP_CHECK=1
rm -f oc.img serial.log qemu.log
dd if=/dev/zero of=oc.img bs=1M count=512 status=none
/usr/sbin/mkfs.vfat -F 32 -n OPENCORE oc.img >/dev/null 2>&1 || { echo "mkfs failed"; exit 1; }
mmd -i oc.img ::/EFI ::/EFI/BOOT ::/EFI/OC ::/EFI/OC/Drivers >/dev/null 2>&1
mcopy -i oc.img esp/EFI/BOOT/BOOTx64.efi ::/EFI/BOOT/
mcopy -i oc.img esp/EFI/OC/OpenCore.efi ::/EFI/OC/
mcopy -i oc.img esp/EFI/OC/config.plist ::/EFI/OC/
for d in esp/EFI/OC/Drivers/*.efi; do mcopy -i oc.img "$d" ::/EFI/OC/Drivers/; done
echo "drivers actually in the image:"
mdir -i oc.img ::/EFI/OC/Drivers 2>/dev/null | grep -i " EFI "
cp /usr/share/OVMF/OVMF_VARS_4M.fd "$HOME/oc/vars.fd"
echo "rebuilt at $(date +%H:%M:%S)"

#!/bin/bash
# Boot the Lion install in a VM, alongside the running Linux.
#
# The physical disk is the qcow2's BACKING file and is opened read-only; every
# write the VM makes lands in the overlay. The failing disk is never written.
#
# -cpu host, not a named model: this host has no SSE4.1, so a "Penryn" profile
# would advertise features KVM cannot provide. The host CPU is literally what
# Lion shipped on, which is the best possible model for it.
#
# isa-applesmc is mandatory -- macOS refuses to boot without the SMC present.
cd "$HOME/oc"
OVMF_CODE=/usr/share/OVMF/OVMF_CODE_4M.fd
exec qemu-system-x86_64 \
  -name lion \
  -accel kvm \
  -machine q35 \
  -cpu host,vendor=GenuineIntel \
  -m 3072 -smp ${SMP:-2} \
  -device isa-applesmc,osk="ourhardworkbythesewordsguardedpleasedontsteal(c)AppleComputerInc" \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,file="$HOME/oc/vars.fd" \
  -drive id=ocdisk,if=none,format=raw,file="$HOME/oc/oc.img" \
  -device ide-hd,drive=ocdisk,bus=ide.0 \
  -drive id=liondisk,if=none,format=qcow2,file=/var/lib/lion-vm/lion-overlay.qcow2 \
  -device ide-hd,drive=liondisk,bus=ide.1 \
  -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 \
  -device e1000-82545em,netdev=n0 \
  -usb -device usb-kbd -device usb-tablet \
  -monitor unix:/tmp/lion-monitor,server,nowait \
  -serial file:"$HOME/oc/serial.log" \
  -vnc 127.0.0.1:1 \
  -display none \
  -boot menu=off

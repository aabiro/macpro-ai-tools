#!/usr/bin/env python3
"""Assemble a minimal OpenCore ESP that can boot an existing Mac OS X install.

Built from OpenCore's own Sample.plist rather than hand-written, because
OpenCore refuses to start if required keys are missing and a hand-rolled config
fails in ways that look like hardware problems.
"""
import plistlib, shutil, os, sys

SRC = os.path.expanduser("~/oc/x/X64")
OUT = os.path.expanduser("~/oc/esp")
SAMPLE = os.path.expanduser("~/oc/x/Docs/Sample.plist")

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(f"{OUT}/EFI/BOOT", exist_ok=True)
os.makedirs(f"{OUT}/EFI/OC/Drivers", exist_ok=True)
for d in ("ACPI", "Kexts", "Tools", "Resources"):
    os.makedirs(f"{OUT}/EFI/OC/{d}", exist_ok=True)

shutil.copy(f"{SRC}/EFI/BOOT/BOOTx64.efi", f"{OUT}/EFI/BOOT/BOOTx64.efi")
shutil.copy(f"{SRC}/EFI/OC/OpenCore.efi", f"{OUT}/EFI/OC/OpenCore.efi")
# OpenRuntime is mandatory. HfsPlus.efi is what lets OpenCore SEE the HFS+
# volume at all -- without it the picker finds nothing and looks broken.
shutil.copy(f"{SRC}/EFI/OC/Drivers/OpenRuntime.efi", f"{OUT}/EFI/OC/Drivers/OpenRuntime.efi")
shutil.copy(os.path.expanduser("~/oc/hfsplus.efi"), f"{OUT}/EFI/OC/Drivers/HfsPlus.efi")

with open(SAMPLE, "rb") as f:
    cfg = plistlib.load(f)

# --- only the settings that matter for booting an existing install in QEMU ---
cfg["Misc"]["Security"]["ScanPolicy"] = 0          # scan every device, any filesystem
cfg["Misc"]["Security"]["SecureBootModel"] = "Disabled"
cfg["Misc"]["Security"]["Vault"] = "Optional"      # we are not signing anything
cfg["Misc"]["Boot"]["Timeout"] = 5
cfg["Misc"]["Boot"]["ShowPicker"] = True
cfg["Misc"]["Boot"]["PickerMode"] = "Builtin"
cfg["Misc"]["Debug"]["Target"] = 67                # log to screen and file
cfg["Misc"]["Debug"]["DisplayLevel"] = 2147483714

# Drivers must be listed, not merely present on disk.
cfg["UEFI"]["Drivers"] = [
    {"Arguments": "", "Comment": "", "Enabled": True, "Path": "OpenRuntime.efi", "LoadEarly": False},
    {"Arguments": "", "Comment": "", "Enabled": True, "Path": "HfsPlus.efi", "LoadEarly": False},
]
cfg["UEFI"]["ConnectDrivers"] = True

# Verbose boot: on a machine where the screen is the only diagnostic, seeing
# the kernel talk is the difference between debugging and guessing.
cfg["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] = b"-v keepsyms=1"

# Empty the sample's example entries so nothing bogus is injected.
for sect, key in (("ACPI", "Add"), ("ACPI", "Delete"), ("ACPI", "Patch"),
                  ("Kernel", "Add"), ("Kernel", "Block"), ("Kernel", "Patch"),
                  ("Misc", "Entries"), ("Misc", "Tools"),
                  ("UEFI", "ReservedMemory")):
    if sect in cfg and key in cfg[sect]:
        cfg[sect][key] = []

with open(f"{OUT}/EFI/OC/config.plist", "wb") as f:
    plistlib.dump(cfg, f)

print("  built:", OUT)
for root, _, files in os.walk(OUT):
    for fn in files:
        p = os.path.join(root, fn)
        print("    %-52s %d bytes" % (p.replace(OUT + "/", ""), os.path.getsize(p)))

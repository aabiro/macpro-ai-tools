import plistlib
p = "/home/macpro/oc/esp/EFI/OC/config.plist"
c = plistlib.load(open(p, "rb"))
# ESP is partition 1: start LBA 40 (0x28), size 409600 sectors (0x64000).
esp_guid = "B7CBC6D0-E273-4628-9C84-3AA61B22F6F3"
dp = ("PciRoot(0x0)/Pci(0x1F,0x2)/Sata(0x1,0xFFFF,0x0)"
      "/HD(1,GPT,%s,0x28,0x64000)"
      "/EFI\\APPLE64\\boot.efi" % esp_guid)
# boot-uuid tells Apple's boot.efi which volume holds the system, since the
# loader is no longer sitting on that volume itself.
args = "-v keepsyms=1 boot-uuid=AB591134-A1EE-3898-93B7-B4BECBF269B0"
c["Misc"]["Entries"] = [{
    "Arguments": args, "Auxiliary": False,
    "Comment": "64-bit boot.efi extracted from the Apple fat container, on the ESP",
    "Enabled": True, "Flavour": "Auto", "Name": "Lion 64", "Path": dp,
    "TextMode": False,
}]
c["Misc"]["Boot"]["ShowPicker"] = True
c["Misc"]["Boot"]["Timeout"] = 3
plistlib.dump(c, open(p, "wb"))
print("    entry Path:", dp)
print("    Arguments :", args)

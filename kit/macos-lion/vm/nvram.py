import plistlib, sys
p="/home/macpro/oc/esp/EFI/OC/config.plist"
c=plistlib.load(open(p,"rb"))
G="7C436110-AB2A-4BBB-A880-FE41995C9F82"      # Apple's boot variable GUID
val=sys.argv[1]
nv=c.setdefault("NVRAM",{})
add=nv.setdefault("Add",{}); dl=nv.setdefault("Delete",{})
add.setdefault(G,{})["boot-args"]=val
# Delete first, then Add, or an existing value wins and the change is silent.
d=dl.setdefault(G,[])
if "boot-args" not in d: d.append("boot-args")
nv["WriteFlash"]=True
c["Misc"]["Entries"][0]["Arguments"]=""        # NVRAM is the channel now
plistlib.dump(c,open(p,"wb"))
print("    NVRAM boot-args = %r  (WriteFlash=True, Delete-then-Add)" % val)

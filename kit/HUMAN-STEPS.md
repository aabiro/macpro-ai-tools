# Human Steps — what still needs a person

Everything else is done. These need you because they need either a password, a
GUI, or physical presence at the machine.

State as of writing: booted `Lion` (disk0s3). `El Capitan` installer app
assembled in /Applications (5.8 GB, verified). `Installer` partition ready
(23 GiB). `Liferaft` backup intact. Debian USB written and checksum-verified.

---

## 1. Create the El Capitan install media  (GUI only)

MacPostFactor has no command-line interface, so this cannot be automated.

    open "/Volumes/MacPostFactor v2.0/MacPostFactor.app"

    OS version    : El Capitan (10.11)
    Installer app : /Applications/Install OS X El Capitan.app
    Destination   : Installer          <-- 23 GiB

WARNING - four HFS+ volumes are mounted. Read the size before committing:

    Installer     23 GiB      the install MEDIA          <-- destination
    El Capitan    149.9 GB    the install TARGET (later)
    Lion          825 GB      your working system
    Liferaft      999.9 GB    your only backup

## 2. Boot 4 - install El Capitan

Restart, hold Option, choose `Installer`. Install to the `El Capitan` 149.9 GB
volume. An internal partition, so none of the USB boot flakiness applies.

Afterwards confirm with:  df -h /

## 3. Boot 5 - install Debian   *** ONE-WAY: ERASES LIFERAFT ***

Debian USB into a REAR port. Nothing else plugged in.
Restart, hold Option, choose `EFI Boot` or `Windows` (orange external icon),
then `Install`.

At the partitioner select the Seagate ST31000333AS.
Match on MODEL, never on disk number - numbering moves between boots, and the
Samsung HD103SI holds Lion and El Capitan.

## 4. Boot 6 - provision Linux

    chmod +x bootstrap.sh
    ./bootstrap.sh --dry-run      # preview, changes nothing
    ./bootstrap.sh                # toolchains, Docker, claude/gemini/aider
    sudo macpro-doctor            # real SMART data Lion could never show

---

## Optional

Reclaim the installer partition once El Capitan is installed:

    sudo diskutil eraseVolume free n disk0s4
    sudo diskutil resizeVolume disk0s3 R

Stop having to hold Option at every boot:

    sudo bless --mount /Volumes/Lion --setBoot

Delete the 6 GB extraction scratch (kept only as a re-copy fallback):

    rm -rf /Users/Shared/elcap-extract

Revoke the automation account's access before handover:

    sudo dseditgroup -o edit -d ai-cockpit -t user admin
    rm /Users/ai-cockpit/.ssh/authorized_keys

---

## Two cautions

DO NOT run scrub.sh. The recipient owns the `administrator` account, so it
would delete their own files. It is retained only for a future handover to a
different person.

Change the account password. It was shared in a chat transcript.

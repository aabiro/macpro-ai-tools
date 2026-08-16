#!/bin/bash
#
# scrub.sh -- remove the previous owner's data before this Mac changes hands.
#
# RUN THIS FROM AN ADMINISTRATOR ACCOUNT. It needs sudo.
#
#     ./scrub.sh                        preview only -- changes nothing
#     ./scrub.sh --archive /Volumes/USB copy data off first, then preview
#     ./scrub.sh --apply                actually delete (asks you to type YES)
#
# Recommended order:
#     1. ./scrub.sh                              see what is there
#     2. ./scrub.sh --archive /Volumes/MyDrive   save it somewhere safe
#     3. ./scrub.sh --archive /Volumes/MyDrive --apply
#
# What it removes:
#   - the entire /Users/administrator account and its data
#   - SSH authorized_keys (otherwise the previous owner keeps remote access)
#   - shell history on all accounts
#   - the old prototype scripts referencing a private Tailscale address
#   - saved AI Cockpit settings pointing at the old network
#
# What it deliberately leaves alone:
#   - /Users/Shared/ai-cockpit  (the kit the new owner needs)
#   - the Liferaft backup clone on the second drive
#   - anything on /Volumes other than an archive target you name
#
set -uo pipefail

APPLY=0
ARCHIVE=""
TARGET_USER="administrator"
KEEP_USER="ai-cockpit"

while [ $# -gt 0 ]; do
    case "$1" in
        --apply)   APPLY=1; shift ;;
        --archive) ARCHIVE="${2:-}"; shift 2 ;;
        --user)    TARGET_USER="${2:-}"; shift 2 ;;
        -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
    esac
done

if [ -t 1 ]; then B=$'\033[1m'; R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; Z=$'\033[0m'
else B=""; R=""; G=""; Y=""; Z=""; fi

banner() { printf '\n%s== %s ==%s\n' "$B" "$*" "$Z"; }
item()   { printf '   %s\n' "$*"; }
act()    { printf '   %s->%s %s\n' "$G" "$Z" "$*"; }
warn()   { printf '   %s!!%s %s\n' "$R" "$Z" "$*"; }

if [ "$(id -u)" != "0" ]; then
    if ! sudo -v 2>/dev/null; then
        echo "This script needs administrator rights. Run it from an admin account." >&2
        exit 1
    fi
    SUDO="sudo"
else
    SUDO=""
fi

if [ "$APPLY" = "1" ]; then
    printf '%s' "$R"
    cat <<'EOF'
+--------------------------------------------------------------+
|                      DESTRUCTIVE MODE                        |
|  Files will be permanently deleted. There is no undo, and no  |
|  Trash. Make sure you have archived anything you want first.  |
+--------------------------------------------------------------+
EOF
    printf '%s' "$Z"
else
    printf '\n%sPREVIEW MODE -- nothing will be changed.%s\n' "$Y" "$Z"
    printf 'Re-run with --apply once you are happy with the list below.\n'
fi

# ---------------------------------------------------------------------------
banner "1. The $TARGET_USER account"
# ---------------------------------------------------------------------------
HOME_DIR="/Users/$TARGET_USER"
if [ -d "$HOME_DIR" ]; then
    SIZE=$($SUDO du -sh "$HOME_DIR" 2>/dev/null | cut -f1)
    item "location : $HOME_DIR"
    item "size     : ${SIZE:-unknown}"
    for d in Desktop Documents Downloads Movies Music Pictures Sites projects .Trash .ssh; do
        if $SUDO test -d "$HOME_DIR/$d"; then
            N=$($SUDO ls -1 "$HOME_DIR/$d" 2>/dev/null | wc -l | tr -d ' ')
            item "  $d: $N entries"
        fi
    done
else
    item "no such account -- nothing to do"
fi

# ---------------------------------------------------------------------------
banner "2. SSH access held by the previous owner"
# ---------------------------------------------------------------------------
FOUND_KEYS=0
for u in "$TARGET_USER" "$KEEP_USER"; do
    AK="/Users/$u/.ssh/authorized_keys"
    if $SUDO test -f "$AK"; then
        FOUND_KEYS=1
        N=$($SUDO grep -c "^ssh-" "$AK" 2>/dev/null || echo 0)
        warn "$AK holds $N key(s) -- grants remote login AFTER handover"
        $SUDO awk '{print "        " substr($0,1,50) "..."}' "$AK" 2>/dev/null | head -4
    fi
done
[ "$FOUND_KEYS" = "0" ] && item "none found"

# ---------------------------------------------------------------------------
banner "3. Shell history"
# ---------------------------------------------------------------------------
for u in "$TARGET_USER" "$KEEP_USER"; do
    for f in .bash_history .zsh_history .sh_history; do
        H="/Users/$u/$f"
        if $SUDO test -f "$H"; then
            N=$($SUDO wc -l < "$H" 2>/dev/null | tr -d ' ')
            item "$H ($N lines)"
        fi
    done
done

# ---------------------------------------------------------------------------
banner "4. Old prototypes referencing the previous owner's network"
# ---------------------------------------------------------------------------
OLD_FILES=""
for f in /Users/$KEEP_USER/cockpit.py /Users/$KEEP_USER/g5-doctor.py \
         /Users/$KEEP_USER/oracle.py /Users/$KEEP_USER/test_client.py; do
    if [ -f "$f" ]; then
        OLD_FILES="$OLD_FILES $f"
        REF=$(grep -oE '100\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.[0-9]+\.[0-9]+' "$f" 2>/dev/null | head -1)
        item "$f${REF:+  (references $REF)}"
    fi
done
[ -z "$OLD_FILES" ] && item "none found"

# ---------------------------------------------------------------------------
banner "5. Saved AI Cockpit settings"
# ---------------------------------------------------------------------------
CFG_FOUND=0
for u in "$TARGET_USER" "$KEEP_USER"; do
    C="/Users/$u/.g5ai.json"
    if $SUDO test -f "$C"; then
        CFG_FOUND=1
        GW=$($SUDO grep -o '"gateway"[^,}]*' "$C" 2>/dev/null | head -1)
        item "$C  $GW"
    fi
done
[ "$CFG_FOUND" = "0" ] && item "none found"
item "(the machine-wide /Users/Shared/ai-cockpit/config.json is reset, not removed)"

# ---------------------------------------------------------------------------
banner "Preserved -- NOT touched"
# ---------------------------------------------------------------------------
item "/Users/Shared/ai-cockpit      the kit the new owner needs"
item "/Volumes/Liferaft             the backup clone of this system"
item "the $KEEP_USER account itself (only its keys/history/prototypes go)"

# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------
if [ -n "$ARCHIVE" ]; then
    banner "Archiving to $ARCHIVE"
    if [ ! -d "$ARCHIVE" ]; then
        warn "$ARCHIVE does not exist or is not mounted -- cannot archive"
        exit 1
    fi
    STAMP=$(date +%Y%m%d-%H%M%S)
    DEST="$ARCHIVE/macpro-handover-$STAMP"
    if [ "$APPLY" = "1" ] || [ -n "$ARCHIVE" ]; then
        act "creating $DEST"
        $SUDO mkdir -p "$DEST" || { warn "could not create $DEST"; exit 1; }
        if [ -d "$HOME_DIR" ]; then
            act "copying $HOME_DIR (this may take a while)"
            $SUDO ditto "$HOME_DIR" "$DEST/$TARGET_USER" 2>/dev/null \
                || $SUDO cp -Rp "$HOME_DIR" "$DEST/$TARGET_USER" 2>/dev/null \
                || warn "archive incomplete -- check $DEST before continuing"
            SZ=$($SUDO du -sh "$DEST" 2>/dev/null | cut -f1)
            act "archived ${SZ:-?} to $DEST"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
if [ "$APPLY" != "1" ]; then
    printf '\n%sPreview complete. Nothing was changed.%s\n' "$Y" "$Z"
    printf 'To archive first :  %s --archive /Volumes/YourDrive\n' "$0"
    printf 'To delete        :  %s --apply\n\n' "$0"
    exit 0
fi

if [ -z "$ARCHIVE" ]; then
    printf '\n%sYou have not archived anything. Deletion is permanent.%s\n' "$R" "$Z"
fi
printf '\nType %sYES%s (capitals) to permanently delete everything listed above: ' "$B" "$Z"
read -r CONFIRM
if [ "$CONFIRM" != "YES" ]; then
    printf '\nCancelled. Nothing was changed.\n\n'
    exit 0
fi

banner "Applying"

# 1. the account
if [ -d "$HOME_DIR" ]; then
    if $SUDO dscl . -read "/Users/$TARGET_USER" >/dev/null 2>&1; then
        act "removing the $TARGET_USER account record"
        $SUDO dscl . -delete "/Users/$TARGET_USER" 2>/dev/null \
            || warn "could not remove the account record (delete it in System Preferences)"
    fi
    act "deleting $HOME_DIR"
    $SUDO rm -rf "$HOME_DIR" 2>/dev/null || warn "could not fully delete $HOME_DIR"
fi

# 2. ssh keys
for u in "$TARGET_USER" "$KEEP_USER"; do
    AK="/Users/$u/.ssh/authorized_keys"
    if $SUDO test -f "$AK"; then
        act "removing $AK"
        $SUDO rm -f "$AK"
    fi
done

# 3. history
for u in "$TARGET_USER" "$KEEP_USER"; do
    for f in .bash_history .zsh_history .sh_history; do
        H="/Users/$u/$f"
        $SUDO test -f "$H" && { act "clearing $H"; $SUDO rm -f "$H"; }
    done
done

# 4. old prototypes
for f in $OLD_FILES; do
    act "removing $f"
    $SUDO rm -f "$f"
done
$SUDO rm -f /Users/$KEEP_USER/*.pyc 2>/dev/null

# 5. settings
for u in "$TARGET_USER" "$KEEP_USER"; do
    C="/Users/$u/.g5ai.json"
    $SUDO test -f "$C" && { act "removing $C"; $SUDO rm -f "$C"; }
done

SHARED_CFG="/Users/Shared/ai-cockpit/config.json"
if [ -f "$SHARED_CFG" ]; then
    act "resetting $SHARED_CFG to blank defaults"
    $SUDO tee "$SHARED_CFG" >/dev/null <<'JSON'
{
  "gateway": "",
  "provider": "gemini",
  "model": "",
  "max_tokens": 2048,
  "timeout": 120
}
JSON
    $SUDO chmod 666 "$SHARED_CFG" 2>/dev/null || true
fi

# 6. system-wide leftovers
act "clearing caches and temporary files"
$SUDO rm -rf /private/var/tmp/* 2>/dev/null
$SUDO rm -f /tmp/cockpit-kit.tgz /tmp/kit.tgz 2>/dev/null

cat <<EOF

${G}Scrub complete.${Z}

Still worth doing by hand before the machine leaves:

  1. Sign out of iCloud, iTunes, Messages and Mail
     (System Preferences > iCloud, and the apps themselves)
  2. Deauthorise iTunes:  iTunes > Store > Deauthorise This Computer
  3. Check /Volumes/Liferaft -- it is a clone of the OLD system and still
     contains the previous owner's files. Either erase it, or leave it as a
     recovery option knowingly.
  4. Create an account for the new owner, and confirm it can run:
         /Users/Shared/ai-cockpit/bin/g5-config show

EOF

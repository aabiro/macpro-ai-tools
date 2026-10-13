#!/bin/sh
# Runs INSIDE Lion, from single-user mode, off the FAT ESP.
# Goal: make the VM reachable over SSH with a key, so Linux can run commands in
# Lion without anyone typing a password.
#
# Everything here lands in the qcow2 overlay. The physical disk is read-only.
set -u
LOG=/m/setup.log
exec >"$LOG" 2>&1
echo "=== setup starting: $(date) ==="
echo "--- mounted:"; /sbin/mount

# 1. sshd is present in Lion but disabled until Remote Login is switched on.
#    launchctl is not usable in single-user, so change what launchd reads at boot.
PL=/System/Library/LaunchDaemons/ssh.plist
if [ -f "$PL" ]; then
    cp "$PL" "$PL.orig-$(date +%s)"
    /usr/libexec/PlistBuddy -c "Delete :Disabled" "$PL" 2>/dev/null
    echo "--- ssh.plist Disabled key removed"
fi
OV=/var/db/launchd.db/com.apple.launchd/overrides.plist
if [ -f "$OV" ]; then
    cp "$OV" "$OV.orig-$(date +%s)"
    /usr/libexec/PlistBuddy -c "Delete :com.apple.sshd" "$OV" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Add :com.apple.sshd dict" "$OV" 2>/dev/null
    /usr/libexec/PlistBuddy -c "Add :com.apple.sshd:Disabled bool false" "$OV" 2>/dev/null
    echo "--- launchd override set: com.apple.sshd Disabled=false"
fi

# 2. Key-only root login. No password is set, typed, or stored anywhere.
mkdir -p /var/root/.ssh
chmod 700 /var/root/.ssh
cp /m/lion_key.pub /var/root/.ssh/authorized_keys
chmod 600 /var/root/.ssh/authorized_keys
chown -R root:wheel /var/root/.ssh
echo "--- authorized_keys installed:"; cat /var/root/.ssh/authorized_keys

# 3. Keys only -- passwords explicitly refused, so a blank/guessed password
#    cannot be used to get in.
SC=/etc/sshd_config
[ -f /etc/ssh/sshd_config ] && SC=/etc/ssh/sshd_config
cp "$SC" "$SC.orig-$(date +%s)"
sed -i.bak \
  -e 's/^#*PermitRootLogin.*/PermitRootLogin without-password/' \
  -e 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' \
  -e 's/^#*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' \
  -e 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' "$SC"
grep -E "^(PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|ChallengeResponse)" "$SC"
echo "--- sshd_config: $SC"

echo "=== setup done ==="
sync

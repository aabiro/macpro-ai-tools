# /etc/profile.d/lion.sh -- so nothing has to be exported by hand per session.
# Installed by the handoff kit. See kit/LION-VM.md.

# Where the running Lion VM's files appear. Read-write; the physical disk is
# never touched.
export LION_MOUNT=/mnt/lion-live

# The AI gateway, as the Lion guest sees it. 10.0.2.2 is this machine from
# inside QEMU's user network.
export LION_GATEWAY=http://10.0.2.2:8081

# The same gateway from Linux itself, for tools running on this side.
export AI_GATEWAY=http://127.0.0.1:8081
export OPENAI_BASE_URL=http://127.0.0.1:8081/v1
export OPENAI_API_KEY=${OPENAI_API_KEY:-not-needed-locally}

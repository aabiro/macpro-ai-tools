#!/usr/bin/env bash
#
# bootstrap.sh -- provision a fresh Debian/Ubuntu install on the Mac Pro 1,1
#                 as a modern, AI-capable development machine.
#
# Run it AFTER installing Linux (see LINUX-STARTER-PACK.md).
#
#     chmod +x bootstrap.sh
#     ./bootstrap.sh                  # do it
#     ./bootstrap.sh --dry-run        # show what it would do, change nothing
#     ./bootstrap.sh --help           # all options
#
# Safe to re-run: every step checks whether it has already been done.
#
set -uo pipefail

VERSION="1.0.0"

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
DRY_RUN=0
DO_BASE=1
DO_DEV=1
DO_DOCKER=1
DO_NODE=1
DO_AI=1
DO_OLLAMA=0        # off by default: honestly too slow to be useful here
DO_GATEWAY=1
DO_TUNING=1

usage() {
    sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
    cat <<'EOF'

Options:
  --dry-run        Print every command instead of running it
  --no-base        Skip system update and core utilities
  --no-dev         Skip build tools, git, Python tooling
  --no-docker      Skip Docker
  --no-node        Skip Node.js
  --no-ai          Skip the AI command-line tools
  --with-ollama    Install Ollama for local models (SLOW on this hardware)
  --no-gateway     Skip installing the vintage-Mac gateway service
  --no-tuning      Skip old-hardware tuning
  -h, --help       This message
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run)     DRY_RUN=1 ;;
        --no-base)     DO_BASE=0 ;;
        --no-dev)      DO_DEV=0 ;;
        --no-docker)   DO_DOCKER=0 ;;
        --no-node)     DO_NODE=0 ;;
        --no-ai)       DO_AI=0 ;;
        --with-ollama) DO_OLLAMA=1 ;;
        --no-gateway)  DO_GATEWAY=0 ;;
        --no-tuning)   DO_TUNING=0 ;;
        -h|--help)     usage; exit 0 ;;
        *) echo "Unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
if [ -t 1 ]; then
    B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; Z=$'\033[0m'
else
    B=""; G=""; Y=""; R=""; Z=""
fi

STEP_NUM=0
say()  { printf '%s\n' "$*"; }
step() { STEP_NUM=$((STEP_NUM + 1)); printf '\n%s==> [%d] %s%s\n' "$B" "$STEP_NUM" "$*" "$Z"; }
ok()   { printf '    %sok%s   %s\n' "$G" "$Z" "$*"; }
skip() { printf '    %s--%s   %s\n' "$Y" "$Z" "$*"; }
warn() { printf '    %s!!%s   %s\n' "$R" "$Z" "$*"; }

# Run a command, honouring --dry-run. Never aborts the script on failure --
# a missing optional package should not strand a half-provisioned machine.
run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '    would run: %s\n' "$*"
        return 0
    fi
    if ! "$@"; then
        warn "command failed: $*"
        return 1
    fi
    return 0
}

have() { command -v "$1" >/dev/null 2>&1; }

# sudo wrapper: works whether or not we are already root
SUDO=""
if [ "$(id -u)" != "0" ]; then
    if have sudo; then
        SUDO="sudo"
    else
        echo "This script needs root access, and sudo is not installed." >&2
        echo "Either run it as root, or install sudo first." >&2
        exit 1
    fi
fi

apt_install() {
    local missing=()
    for pkg in "$@"; do
        if dpkg -s "$pkg" >/dev/null 2>&1; then
            continue
        fi
        missing+=("$pkg")
    done
    if [ ${#missing[@]} -eq 0 ]; then
        skip "already installed: $*"
        return 0
    fi
    run $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}" \
        && ok "installed: ${missing[*]}"
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
cat <<EOF
${B}Mac Pro 1,1 Linux Starter Pack  v${VERSION}${Z}

  Host    : $(hostname)
  Kernel  : $(uname -r)
  Distro  : $( . /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-unknown}" )
  CPU     : $(nproc 2>/dev/null || echo '?') cores
  Memory  : $(awk '/MemTotal/ {printf "%.1f GB", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo '?')
  Mode    : $( [ "$DRY_RUN" = "1" ] && echo "DRY RUN - nothing will change" || echo "live" )
EOF

if ! have apt-get; then
    warn "This script targets Debian/Ubuntu (apt). Yours is different -- stopping."
    exit 1
fi

if ! ping -c1 -W3 deb.debian.org >/dev/null 2>&1 && ! ping -c1 -W3 archive.ubuntu.com >/dev/null 2>&1; then
    warn "No network. Plug in an Ethernet cable -- the 2006 AirPort card is unreliable."
    [ "$DRY_RUN" = "1" ] || exit 1
fi

TARGET_USER="${SUDO_USER:-$(id -un)}"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
say "  User    : $TARGET_USER ($TARGET_HOME)"

# ---------------------------------------------------------------------------
# 1. Base system
# ---------------------------------------------------------------------------
if [ "$DO_BASE" = "1" ]; then
    step "Updating the system"
    run $SUDO apt-get update -qq && ok "package lists updated"
    run $SUDO env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && ok "packages upgraded"

    step "Core command-line tools"
    apt_install ca-certificates curl wget gnupg lsb-release \
                git vim nano tmux screen htop tree rsync unzip zip \
                less man-db bash-completion openssh-server ufw
fi

# ---------------------------------------------------------------------------
# 2. Development toolchain
# ---------------------------------------------------------------------------
if [ "$DO_DEV" = "1" ]; then
    step "Build tools and Python"
    apt_install build-essential pkg-config \
                python3 python3-pip python3-venv python3-dev pipx \
                sqlite3 jq

    if have pipx; then
        run pipx ensurepath >/dev/null 2>&1 && ok "pipx on PATH"
    fi
fi

# ---------------------------------------------------------------------------
# 3. Node.js  (needed by the AI command-line tools)
# ---------------------------------------------------------------------------
if [ "$DO_NODE" = "1" ]; then
    step "Node.js"
    if have node && [ "$(node -v | sed 's/v\([0-9]*\).*/\1/')" -ge 20 ] 2>/dev/null; then
        skip "node $(node -v) already present"
    else
        # NodeSource carries current LTS; Debian's own package lags too far
        # behind for the AI CLIs, which expect Node 20+.
        if [ "$DRY_RUN" = "1" ]; then
            say "    would run: NodeSource setup script for Node 22 LTS"
        else
            if curl -fsSL https://deb.nodesource.com/setup_22.x | $SUDO -E bash - >/dev/null 2>&1; then
                apt_install nodejs
            else
                warn "NodeSource unavailable; falling back to the distro package"
                apt_install nodejs npm
            fi
        fi
    fi
    have node && ok "node $(node -v 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# 4. Docker
# ---------------------------------------------------------------------------
if [ "$DO_DOCKER" = "1" ]; then
    step "Docker"
    if have docker; then
        skip "docker already installed"
    else
        # Debian's docker.io is older than Docker's own build but is signed by
        # the distro and needs no third-party key. On a machine that should
        # keep working unattended, that trade is worth it.
        apt_install docker.io docker-compose-v2
    fi
    if have docker; then
        run $SUDO systemctl enable --now docker && ok "docker service enabled"
        if ! id -nG "$TARGET_USER" 2>/dev/null | grep -qw docker; then
            run $SUDO usermod -aG docker "$TARGET_USER" \
                && ok "added $TARGET_USER to the docker group (log out and back in)"
        else
            skip "$TARGET_USER already in the docker group"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 5. AI command-line tools
# ---------------------------------------------------------------------------
if [ "$DO_AI" = "1" ]; then
    step "AI command-line tools"

    if have npm; then
        for spec in "@anthropic-ai/claude-code:claude" "@google/gemini-cli:gemini"; do
            pkg="${spec%%:*}"; cmd="${spec##*:}"
            if have "$cmd"; then
                skip "$cmd already installed"
            else
                run $SUDO npm install -g "$pkg" && ok "installed $cmd"
            fi
        done
    else
        warn "npm missing -- skipping claude and gemini (re-run without --no-node)"
    fi

    if have pipx; then
        if have aider; then
            skip "aider already installed"
        else
            run pipx install aider-chat && ok "installed aider"
        fi
    fi

    cat <<'EOF'

    These talk to cloud services directly -- unlike the Lion side, no gateway
    is needed here, because Linux has modern TLS.

    First run walks you through signing in:
        claude          Anthropic Claude Code
        gemini          Google Gemini CLI
        aider           multi-provider pair programmer
EOF
fi

# ---------------------------------------------------------------------------
# 6. Ollama (optional, and slow here)
# ---------------------------------------------------------------------------
if [ "$DO_OLLAMA" = "1" ]; then
    step "Ollama (local models)"
    warn "This machine has ~6 GB RAM, no usable GPU, and 2006 CPU cores."
    warn "Expect roughly 1-3 tokens/second on a 3B model. Fun once; not practical."
    if have ollama; then
        skip "ollama already installed"
    elif [ "$DRY_RUN" = "1" ]; then
        say "    would run: Ollama install script from https://ollama.com/install.sh"
    else
        curl -fsSL https://ollama.com/install.sh | sh && ok "ollama installed"
        say "    Try the smallest useful model:  ollama run qwen2.5:1.5b"
    fi
fi

# ---------------------------------------------------------------------------
# 7. Vintage-Mac gateway service
# ---------------------------------------------------------------------------
if [ "$DO_GATEWAY" = "1" ]; then
    step "Vintage-Mac AI gateway"
    GW_SRC=""
    for candidate in "./aigw.py" "../gateway/aigw.py" "/opt/ai-gateway/aigw.py"; do
        [ -f "$candidate" ] && { GW_SRC="$candidate"; break; }
    done

    if [ -z "$GW_SRC" ]; then
        skip "aigw.py not found next to this script -- skipping"
        say  "    (copy it from the Lion drive: /Users/Shared/ai-cockpit/gateway/aigw.py)"
    else
        run $SUDO mkdir -p /opt/ai-gateway
        run $SUDO cp "$GW_SRC" /opt/ai-gateway/aigw.py
        run $SUDO chmod 755 /opt/ai-gateway/aigw.py

        if [ ! -f /etc/ai-gateway.env ]; then
            if [ "$DRY_RUN" = "1" ]; then
                say "    would create /etc/ai-gateway.env (API key file, mode 0600)"
            else
                printf '# Uncomment one and paste your key.\n#GEMINI_API_KEY=\n#ANTHROPIC_API_KEY=\n#OPENAI_API_KEY=\n' \
                    | $SUDO tee /etc/ai-gateway.env >/dev/null
                $SUDO chmod 600 /etc/ai-gateway.env
                ok "created /etc/ai-gateway.env (add your key there)"
            fi
        else
            skip "/etc/ai-gateway.env already exists"
        fi

        if [ "$DRY_RUN" = "1" ]; then
            say "    would install the ai-gateway systemd service"
        else
            $SUDO tee /etc/systemd/system/ai-gateway.service >/dev/null <<'UNIT'
[Unit]
Description=Vintage Mac AI Gateway
Documentation=file:/opt/ai-gateway/aigw.py
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/etc/ai-gateway.env
ExecStart=/usr/bin/python3 /opt/ai-gateway/aigw.py --port 8081
Restart=on-failure
RestartSec=5
DynamicUser=yes
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
UNIT
            run $SUDO systemctl daemon-reload
            ok "service installed (not started -- add a key first)"
            say "    Then:  sudo systemctl enable --now ai-gateway"
        fi
        say ""
        say "    Note: this serves OTHER vintage machines on your network."
        say "    It cannot serve this machine's own Lion system -- only one"
        say "    operating system runs at a time."
    fi
fi

# ---------------------------------------------------------------------------
# 7b. The machine's own documentation and health tool
# ---------------------------------------------------------------------------
step "Machine documentation and health tool"

# macpro-doctor: the Linux successor to Lion's g5-doctor. It reports far more,
# because Lion had no smartctl -- there SMART was a single pass/fail word.
DOC_SRC=""
for c in "./macpro-doctor" "$(dirname "$0")/macpro-doctor"; do
    [ -f "$c" ] && { DOC_SRC="$c"; break; }
done
if [ -n "$DOC_SRC" ]; then
    run $SUDO install -m 755 "$DOC_SRC" /usr/local/bin/macpro-doctor \
        && ok "installed macpro-doctor (run: sudo macpro-doctor)"
else
    skip "macpro-doctor not found next to this script"
fi

# Docs travel with the machine. /usr/local/share/doc is the correct home for
# locally-installed documentation under the FHS.
DOCDIR="/usr/local/share/doc/macpro"
FOUND_DOCS=0
for d in ./*.md "$(dirname "$0")"/*.md "$(dirname "$0")"/../docs/*.md; do
    [ -f "$d" ] || continue
    [ "$FOUND_DOCS" = "0" ] && run $SUDO mkdir -p "$DOCDIR"
    run $SUDO install -m 644 "$d" "$DOCDIR/" && FOUND_DOCS=$((FOUND_DOCS + 1))
done

# The Lion partition still holds the full kit. Pull the docs across if it is
# mounted -- HFS+ reads fine on Linux, so nothing is lost in the migration.
for hfs in /mnt/Lion /media/*/Lion "/media/$TARGET_USER/Lion"; do
    [ -d "$hfs/Users/Shared/ai-cockpit/docs" ] || continue
    run $SUDO mkdir -p "$DOCDIR"
    run $SUDO cp -n "$hfs/Users/Shared/ai-cockpit/docs/"*.md "$DOCDIR/" 2>/dev/null
    ok "recovered docs from the Lion partition at $hfs"
    break
done

if [ "$FOUND_DOCS" -gt 0 ] || [ -d "$DOCDIR" ]; then
    ok "docs in $DOCDIR"
    say "    $(ls "$DOCDIR" 2>/dev/null | tr '\n' ' ')"
else
    skip "no docs found to install"
    say "    They are on the Lion partition: /Users/Shared/ai-cockpit/docs/"
    say "    Mount it and re-run, or copy them by hand."
fi

# ---------------------------------------------------------------------------
# 8. Old-hardware tuning
# ---------------------------------------------------------------------------
if [ "$DO_TUNING" = "1" ]; then
    step "Tuning for 2006 hardware"

    # 6 GB of RAM with mechanical disks: swapping hurts badly, so lean on RAM.
    if [ -f /etc/sysctl.d/99-macpro.conf ]; then
        skip "sysctl tuning already applied"
    elif [ "$DRY_RUN" = "1" ]; then
        say "    would write /etc/sysctl.d/99-macpro.conf (swappiness, writeback)"
    else
        $SUDO tee /etc/sysctl.d/99-macpro.conf >/dev/null <<'SYSCTL'
# Mac Pro 1,1: 6 GB RAM, mechanical disks. Swapping to spinning rust is
# painful, so hold pages in RAM longer than the default.
vm.swappiness=10
vm.vfs_cache_pressure=50
SYSCTL
        run $SUDO sysctl --system >/dev/null && ok "sysctl tuning applied"
    fi

    # Hardware telemetry. Lion could only report SMART as a pass/fail word;
    # here we can read the numbers that actually predict a failure.
    apt_install smartmontools lm-sensors dmidecode

    # The FB-DIMM memory controller driver. Without it a failing DIMM gives no
    # warning at all until it panics -- and FB-DIMM failure is the single most
    # common way this model dies.
    if [ "$DRY_RUN" = "1" ]; then
        say "    would load i5000_edac (FB-DIMM ECC monitoring)"
    else
        if $SUDO modprobe i5000_edac 2>/dev/null; then
            ok "i5000_edac loaded -- ECC errors will now be counted"
            grep -q "^i5000_edac" /etc/modules 2>/dev/null || \
                echo "i5000_edac" | $SUDO tee -a /etc/modules >/dev/null
        else
            skip "i5000_edac not available (expected if this is not a Mac Pro 1,1)"
        fi
    fi

    if have smartctl; then
        ok "smartctl available -- both drives are ~2009-era, check them"
        say "    Watch: Reallocated_Sector_Ct, Current_Pending_Sector, Power_On_Hours"
    fi

    # Firewall: sensible default for a machine that may face the internet.
    if have ufw; then
        if $SUDO ufw status 2>/dev/null | grep -q "Status: active"; then
            skip "ufw already active"
        elif [ "$DRY_RUN" = "1" ]; then
            say "    would enable ufw allowing SSH"
        else
            $SUDO ufw allow OpenSSH >/dev/null 2>&1
            $SUDO ufw --force enable >/dev/null 2>&1 && ok "firewall enabled (SSH allowed)"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
cat <<EOF

${B}Finished.${Z}

  What you have now:
    - Current Debian/Ubuntu with modern TLS (the Lion problem is gone)
    - Build tools, Python, Node.js$( have docker && echo ", Docker" )
    - AI tools: claude, gemini, aider
    - SMART monitoring on both ageing drives
    - Firewall on, SSH allowed

  Next:
    1. Log out and back in (for the docker group and PATH changes)
    2. Run:  claude
    3. Check the drives:  sudo smartctl -a /dev/sda

  Reminder: both disks are ~2009 mechanical drives well past their service
  life. Keep backups off this machine.
EOF

[ "$DRY_RUN" = "1" ] && say "\n(Dry run -- nothing was actually changed.)"
exit 0

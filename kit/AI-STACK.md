# The AI stack on this machine

Everything installed, where it listens, and what it needs to work. Read
[LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) first if the screen is
black — that is a separate, known problem.

The governing constraint for all of it: these are **x86-64-v1** Xeons (2006, no
SSE4.1/SSE4.2/POPCNT). Anything shipping a modern precompiled binary tends to
die instantly with `Illegal instruction`. Every tool below was tested for that
before being called working.

---

## Services

| Service | Port | What it is |
|---|---|---|
| `ai-gateway` | **8081** | `aigw.py`. TLS bridge so Lion can reach model APIs. |
| `cockpit-web` | **3000** | Next.js console: Oracle / Custodian / Retro-Coder / Status. |
| `code-server` | **8443** | VS Code in a browser, extensions and all. |
| `lightdm` | — | XFCE desktop on the physical screen. |
| `tailscaled` | 41641/udp | Remote access. |

From another machine on the LAN, replacing the IP as needed:

```
http://192.168.1.124:3000/     cockpit
http://192.168.1.124:8443/     editor  (password below)
http://192.168.1.124:8081/health   gateway health
```

**Why code-server rather than desktop VS Code:** the heavy process runs here and
the UI runs in your laptop's browser. That is the right shape for a 2006 machine
— the alternative is an Electron app rendering through an unaccelerated
framebuffer. Desktop VS Code would also be a coin-flip on this CPU.

### Credentials

| What | Where |
|---|---|
| Model API keys | `/etc/ai-cockpit/env` — `root:aigw`, mode 0640 |
| code-server password | `/home/macpro/.config/code-server/config.yaml`, mode 0600 |

**Nothing works until the keys are filled in.** Both consoles report
`providers_configured: []` and refuse requests until then:

```bash
sudo nano /etc/ai-cockpit/env
sudo systemctl restart ai-gateway cockpit-web
curl -s localhost:8081/health
```

`ai-gateway` and `cockpit-web` deliberately share that one file, so there is a
single place to rotate credentials.

## Command-line tools

| Command | Version | Note |
|---|---|---|
| `claude` | 1.0.128 | **Pinned.** 2.x is a native binary and SIGILLs — see LINUX-BOOT-AND-DISPLAY.md §8 |
| `claude-dark20` | 1.0.127 | dark-themed Claude Code build, pure JS |
| `claude-desktop` | 1.26832.0 | Electron GUI; works because Chromium dispatches on CPU features at runtime |
| `gemini` | 0.55.1 | |
| `codex` | 0.0.2505291658 | last **TypeScript** release; current ones are Rust binaries |
| `gh` | 2.46.0 | GitHub CLI |
| `g5-codex` | — | read files, propose a patch, show a diff |
| `g5-copilot` | — | suggest/explain a shell command, never runs it |
| `g5-gemini` | — | conversation |
| `ai-session` | — | `tmux` workspace that survives disconnects |

The `g5-*` trio exists because **none of the tools above run on Lion** — Python
2.7 with OpenSSL 0.9.8 cannot negotiate TLS 1.2 with any provider. They proxy
through `ai-gateway`, so the same three commands work on both OSes.

## MCP servers (agent tools for `claude`)

```
$ claude mcp list
filesystem  ✓  scoped to /home/macpro/projects
memory      ✓  persistent notes across sessions
git         ✓  read history, diffs, blame
fetch       ✓  retrieve URLs
time        ✓  timezone-aware clock
```

`filesystem` is deliberately scoped to `~/projects` rather than `/`. Widen it
only if you mean to:

```bash
claude mcp remove filesystem
claude mcp add filesystem -s user -- npx -y @modelcontextprotocol/server-filesystem /path
```

## Host hardening and tuning

- **nftables** (`/etc/nftables.conf`) — default-drop inbound. SSH, 3000, 8081
  and 8443 are open to `192.168.0.0/16` and to `tailscale0` only. The services
  bind `0.0.0.0` and have little or no auth of their own, so **this ruleset is
  the actual security boundary. Do not port-forward any of these.**
- **zram** — 2.9 GB zstd-compressed swap at priority 100, above the 6 GB disk
  swap. With 6 GB of FB-DIMM and mechanical disks, compressing pages in RAM
  beats writing them out; this is the largest perceived-speed win available.
- **unattended-upgrades** — security updates apply automatically. Left on
  deliberately for a machine changing hands.

## What is not installed, and why

| | |
|---|---|
| **Ollama** | binaries require AVX; this CPU has none. Build `llama.cpp` from source instead — it has scalar fallbacks. Expect ~1–3 tok/s for a 1.5B Q4 model. |
| **aider** | needs Python < 3.13; trixie ships only 3.13 |
| **Claude Code 2.x** | Bun-compiled native binary, hard x86-64-v2 floor |
| **Desktop VS Code** | untested Electron gamble; `code-server` is strictly better here |

## Health check

```bash
systemctl status ai-gateway cockpit-web code-server lightdm tailscaled
curl -s localhost:8081/health; curl -s localhost:3000/health
claude mcp list
free -h; /sbin/swapon --show
sudo nft list ruleset | head -20
```

## Before handover

See [LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) §10 — the remote sudo
rule and SSH key must both be removed, and the rule exists in two places.

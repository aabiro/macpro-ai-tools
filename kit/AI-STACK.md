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
| `vscode-web` | **8443** | **Official** VS Code served in a browser. Token in `~/.vscode-web/connection-token`. |
| `lightdm` | — | XFCE desktop on the physical screen. |
| `tailscaled` | 41641/udp | Remote access. |

From another machine on the LAN, replacing the IP as needed:

```
http://192.168.1.124:3000/     cockpit
http://192.168.1.124:8443/     editor  (password below)
http://192.168.1.124:8081/health   gateway health
```

**Official VS Code, not code-server.** code-server was used first because it was
assumed desktop VS Code would not run on an x86-64-v1 CPU. It does — tested,
`rc=0`, zero invalid-opcode traps, same as `claude-desktop`. Official VS Code was
then the better choice for one decisive reason: **it uses Microsoft's
marketplace**, which carries Copilot and Pylance. Open VSX does not and cannot.

You still get the browser experience without code-server, because VS Code ships
its own web server:

```
code serve-web --host 0.0.0.0 --port 8443 --connection-token-file ...
```

That runs as `vscode-web.service` on the same port, so the firewall rule and all
documentation still apply. code-server is stopped, disabled and its unit removed;
the binary is left in place only for rollback and can be deleted with
`rm -rf /usr/local/lib/code-server /usr/local/bin/code-server`.

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

### The gateway speaks OpenAI's dialect

As well as its own simple API, `ai-gateway` now serves the two endpoints every
chat front-end already knows:

```
GET  http://<this-machine>:8081/v1/models
POST http://<this-machine>:8081/v1/chat/completions
```

So any OpenAI-compatible client — on this machine or any other on the network —
can use it, and **the API keys stay in one file on this machine** instead of
being copied into each app. Streaming (`"stream": true`) is supported.

Models are advertised only when their provider has a key, so the list is empty
until `/etc/ai-cockpit/env` is filled in. Exposed names:

| Model | Provider | Notes |
|---|---|---|
| `gemini-pro-latest` | Gemini | strongest; alias, so it will not be retired out from under you |
| `gemini-flash-latest` | Gemini | fast, cheap; the sensible default |
| `gemini-3.1-pro` | Gemini | pinned version |
| `gemini-3.7-flash` | Gemini | pinned version |
| `claude-sonnet-5` | Anthropic | needs `ANTHROPIC_API_KEY` |
| `gpt-4o` | OpenAI | needs `OPENAI_API_KEY` |

> **The `-latest` aliases are the safe choice, and that is not theoretical.**
> While setting this up, `gemini-2.5-pro` and `gemini-2.5-flash` were still
> listed by the API but refused every request with *"no longer available to new
> users"*. A pinned model ID silently becomes dead weight; an alias keeps
> working.

> **Pro models must think.** They reject `thinkingBudget: 0` outright with
> *"This model only works in thinking mode"*, which is exactly what the gateway
> sends by default to save tokens. The OpenAI endpoint therefore tracks a
> per-model thinking flag: on for Pro, off for Flash.

Test it without any client:

```bash
curl -s localhost:8081/v1/models
curl -s localhost:8081/v1/chat/completions -H 'content-type: application/json' \
  -d '{"model":"gemini-flash-latest","messages":[{"role":"user","content":"hello"}]}'
```

## Command-line tools

| Command | Version | Note |
|---|---|---|
| `claude` | 1.0.128 | **Pinned.** 2.x is a native binary and SIGILLs — see LINUX-BOOT-AND-DISPLAY.md §8 |
| `claude-dark20` | 1.0.127 | dark-themed Claude Code build, pure JS |
| `claude-desktop` | 1.26832.0 | Electron GUI; works because Chromium dispatches on CPU features at runtime |
| `gemini` | 0.55.1 | |
| `codex` | 0.0.2505291658 | last **TypeScript** release; current ones are Rust binaries |
| `gh` | 2.46.0 | GitHub CLI |
| `node` / `npm` | 24.19.0 / 11.17.0 | NodeSource. Current Node **does** run on this CPU — tested, see LINUX-BOOT-AND-DISPLAY.md §8 |
| `uv` / `uvx` | 0.12.5 | Python packaging: resolves and installs in seconds where `pip` takes minutes |
| `aider` | 0.86.2 | needs Python <3.13, so it runs on a standalone 3.12 fetched by `uv` |
| `g5-codex` | — | read files, propose a patch, show a diff |
| `g5-copilot` | — | suggest/explain a shell command, never runs it |
| `g5-gemini` | — | conversation |
| `ai-session` | — | `tmux` workspace that survives disconnects |
| `ai` | — | the one command a beginner needs: `setup`, `check`, `fix`, `chat`, `undo` |

The `g5-*` trio exists because **none of the tools above run on Lion** — Python
2.7 with OpenSSL 0.9.8 cannot negotiate TLS 1.2 with any provider. They proxy
through `ai-gateway`, so the same three commands work on both OSes.

## AI assistants in the editor

`code-server` uses Open VSX, and these vendors publish mainly to Microsoft's
marketplace, so what installs is not a free choice:

All four are present in official VS Code:

| Assistant | How |
|---|---|
| **Copilot** | **built into VS Code** — `copilot-chat 0.62.0` ships with it. Nothing to install. |
| **Claude** | `anthropic.claude-code` |
| **Gemini** | `google.geminicodeassist` |
| **ChatGPT / Codex** | `openai.chatgpt` |

This is what official VS Code buys over code-server: on Open VSX, Copilot is
simply not published, and `ms-python.vscode-pylance` is unavailable too. Both
work here.

Plus `ms-python.python`, `eamodio.gitlens`, `timonwong.shellcheck`,
`esbenp.prettier-vscode`, `redhat.vscode-yaml`, the Jupyter suite, and
`mechatroner.rainbow-csv`. Full list: `kit/linux/code-server-extensions.txt`.

**`gh copilot` needs your GitHub account.** Run `gh auth login`, then
`gh extension install github/gh-copilot`.

## MCP servers (agent tools for `claude`)

Eight servers, **59 tools**. The first five are upstream; the last three were
written for this machine.

```
$ claude mcp list        # and: gemini mcp list
filesystem      ✓  14 tools, scoped to /home/macpro/projects
memory          ✓   9 tools, a knowledge graph
git             ✓  12 tools, status/diff/commit/log/branch
fetch           ✓   1 tool
time            ✓   2 tools
macpro-health   ✓   3 tools  <- this machine
macpro-journal  ✓   2 tools  <- this machine
macpro-apt      ✓   3 tools  <- this machine
```

### All eight, in every client that supports MCP

| Client | Config | Servers |
|---|---|---|
| `claude` CLI | `~/.claude.json` (user scope) | **8** |
| `gemini` CLI | `~/.gemini/settings.json` (`-s user --trust`) | **8** |
| **VS Code** | `~/.config/Code/User/mcp.json` | **8** |
| **Claude Desktop** | `~/.config/Claude/claude_desktop_config.json` | **8** |
| **Codex** | `~/.codex/config.toml` (`[mcp_servers.*]`) | **8** |
| `aider` | — | **not supported**: aider 0.86.2 has no MCP client. Not a configuration gap. |

Copies of all five configs live in `kit/linux/mcp-clients/` so a rebuild can
restore them directly.

The VS Code entry covers the editor's own chat **and** its AI extensions, since
Copilot Chat and the others consume VS Code's MCP registry rather than keeping
private ones.

One Gemini gotcha worth knowing: `gemini mcp add` defaults to **project** scope,
so servers added without `-s user` vanish outside that directory. Gemini also
disables MCP entirely in "untrusted folders" — `security.folderTrust.enabled` is
set to `false` in `~/.gemini/settings.json`, without which every server shows as
`Disabled` regardless of configuration.

### The three written here, and why

`/usr/local/bin/macpro-mcp {health|journal|apt}` — one file, three servers,
**every tool read-only**. No write, delete, install or restart exists in it, and
commands are invoked as fixed argv lists so no argument can become a shell
injection.

| Server | Tools | Why |
|---|---|---|
| `macpro-health` | `get_health`, `get_disk_health`, `get_memory_errors` | Diagnosing this machine meant a human pasting command output into a chat window for a week. Now an AI can read it. `get_disk_health` **interprets** rather than reports: it will say *"pending sectors above zero: this drive is failing NOW"*. |
| `macpro-journal` | `list_boots`, `query_journal` | Given how much of this build was "what did the last boot do", an AI that can read boot logs itself is worth having. A missing boot in `list_boots` means the kernel never reached userspace. |
| `macpro-apt` | `search_packages`, `package_info`, `list_upgradable` | Stops the AI guessing whether something is installed. |

`get_disk_health` reads the root-collected telemetry snapshot when running
unprivileged, rather than shelling out to `sudo smartctl` — which would break the
moment the build-time NOPASSWD rule is removed at handover.

## Terminal utilities

Installed for readability and for working over a flaky link:

| Command | What it is |
|---|---|
| `glow` | renders this machine's own markdown docs readably in a terminal |
| `bat` | `cat` with syntax highlighting |
| `tldr` | plain-English command examples (packaged as `tealdeer` in Debian) |
| `mosh` | SSH that survives dropped connections — worth it on a machine that reboots often |
| `rclone` | talks to B2/S3/Drive **and** external drives; the practical backup tool |
| `rg` / `fd` / `fzf` | fast search, find, fuzzy-select |
| `ncdu` | find what is filling the disk |
| `delta` | readable git diffs |
| `pandoc` | document conversion, e.g. the printable sheet to PDF |

Note Debian ships `bat` as `batcat` and `fd` as `fdfind`; symlinks in
`/usr/local/bin` restore the usual names.

Read the docs nicely with:

```bash
glow /usr/local/share/doc/macpro/kit/NEW-OWNER-START-HERE.md
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
- **no screen locker, no display blanking** — `light-locker` is removed and DPMS
  is disabled (autostart runs `xset -dpms s off s noblank`). On this machine a
  blank screen is the signature of the hardware fault in
  LINUX-BOOT-AND-DISPLAY.md §11, so a beginner cannot distinguish a locked
  session from a failure. That ambiguity costs more than the lock protects on a
  home LAN.
- **rasdaemon** — ECC/memory error reporting via the CPU's machine-check banks.
  Required because `i5000_edac` is absent from this kernel, so EDAC can never
  work on this chipset. `sudo ras-mc-ctl --summary` should say "No Memory
  errors"; a rising correctable count is the early warning of a failing DIMM.
  See LINUX-BOOT-AND-DISPLAY.md §11.

## What is not installed, and why

| | |
|---|---|
| **Ollama** | official binaries require AVX and will SIGILL. Building it from source would work but gains nothing: Ollama is a wrapper around the same ggml kernels, so it would run at the same ~1 tok/s measured below. It buys model management, not speed. |
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

## Local model (llama.cpp) — installed, measured, and deliberately not wired in

`llama.cpp` is built at `/opt/llama.cpp` with a model at
`/opt/models/qwen2.5-0.5b-instruct-q4_0.gguf`. It works. It is also too slow
to use conversationally, and the numbers are worth recording so nobody re-treads
this:

```
qwen2 0.6B, 4 threads
                     reading (pp32)   generating (tg32)
  Q4_K_M                  4.72 t/s          0.85 t/s
  Q4_0                   14.03 t/s          1.00 t/s   <- use this one
```

**Use Q4_0, not Q4_K_M.** Q4_K's kernels do more work per weight, which barely
matters when AVX is available and matters enormously when it is not: reading a
prompt is **3x faster** on Q4_0. Generation only improves 18%, because
generation is limited by memory bandwidth (DDR2 FB-DIMM) rather than by
arithmetic, and no quantisation choice fixes that.

At 1 tok/s a paragraph still takes about two minutes. The prompt-reading gain is
what makes short tasks tolerable: a 200-token prompt goes from 42 seconds to 14.

**Build flags matter enormously here.** The first attempt used only
`-DGGML_NATIVE=OFF` to avoid AVX, which drops to the plain x86-64 baseline —
**SSE2 only** — and generated at **0.07 tok/s**. Adding back exactly what this
CPU does implement gave a 12x improvement:

```
-DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_FMA=OFF
-DGGML_F16C=OFF -DGGML_SSE42=OFF -DGGML_BMI2=OFF
-DCMAKE_C_FLAGS="-march=core2 -mtune=core2 -msse3 -mssse3"
```

If you rebuild it, keep those. Removing `-march=core2` costs you 12x; adding AVX
gives an illegal instruction.

**It is not exposed in the cockpit or `ai chat`, on purpose.** A two-minute wait
for one sentence reads as a broken machine, and the new owner is a beginner. Use
it directly if you want it:

```bash
/opt/llama.cpp/build/bin/llama-simple \
  -m /opt/models/qwen2.5-0.5b-instruct-q4_0.gguf \
  -n 64 "your prompt here"
```

Use **`llama-simple`, not `llama-cli`**. `llama-cli` drops into its interactive
prompt on this build even with `-no-cnv` / `--no-conversation`, and emits only
`>` characters when driven non-interactively. `llama-simple` has no interactive
layer and prints the completion directly:

```
$ llama-simple -m .../q4_0.gguf -n 12 "The capital of France is"
The capital of France is Paris, and it is the capital of Europe. It is
```

(That answer is partly wrong, which is what a 0.6B model at this size gives you.
Useful for classification and short factual lookups, not for reasoning.)

Genuinely useful for: short classification, offline single-word answers, and
proving the machine still does something with no internet at all. Not useful
for: conversation, code, or anything you are waiting on.

A faster local model needs different hardware, not different software — see
[HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md).

---

## Lion's AI tools need a gateway on ANOTHER machine — a design constraint

This is the one structural gap in the kit, and it is worth understanding before
anyone spends time on it.

**The premise:** OS X 10.7 Lion has Python 2.7 with OpenSSL 0.9.8, which cannot
negotiate TLS 1.2. It physically cannot reach any modern model API. So the kit
gives it `g5-codex`, `g5-copilot` and `g5-gemini`, which send their requests to
`aigw.py` — a gateway that does the TLS on Lion's behalf.

**The problem:** the gateway runs on the Debian side of this machine, and Lion
and Debian are the same computer. They never run at the same time. **When Lion is
booted, the gateway is switched off with it.**

So out of the box, Lion's AI tools have nothing to talk to. `g5-config show` on
Lion shows an empty gateway, and that is not a misconfiguration — there is
genuinely nothing local to point it at.

### What actually works

Run the gateway on **any other machine on the network** — a laptop, a NAS, a
Raspberry Pi, anything with Python 3. `aigw.py` has **zero dependencies**:

```bash
# on the other machine, once:
export GEMINI_API_KEY=...          # or ANTHROPIC_API_KEY / OPENAI_API_KEY
python3 aigw.py --host 0.0.0.0 --port 8081
```

A copy of `aigw.py` is on Lion at `/Users/Shared/ai-cockpit/gateway/aigw.py`
and on the Debian side at `/opt/ai-cockpit/aigw.py`. Copy it anywhere.

Then, on Lion:

```bash
g5-config set gateway http://<that-machine's-ip>:8081
g5-config test
```

### If there is no other machine

Then Lion has no AI, and that is a hardware fact rather than something to fix.
The options are:

| Option | Notes |
|---|---|
| Use the Debian side for AI | It has everything. This is the sane answer. |
| Run the gateway on a laptop when you want Lion's AI | Works, but only while the laptop is on. |
| Newer macOS on this machine | Needs different CPUs — see HARDWARE-UPGRADE-PATH.md. Even then Lion itself stays stuck. |

**`retro-port` and `g5-doctor` still work without a gateway** for their offline
parts, and `g5-doctor --raw` produces a diagnostic dump you can paste into the
cockpit's Custodian tab from any browser. So Lion is not useless without it —
just not self-sufficient.

### Why not run the gateway on Lion itself?

Because the gateway is the thing that needs TLS 1.2, and Lion is the machine
that cannot do TLS 1.2. Running it there would defeat its only purpose.

---

## Modernisation beyond the AI stack

Added because they change what this 2006 machine can actually do, not because
they are new.

### Containers — the answer to "why not a newer distro"

**`podman 5.4.2` runs containers on this x86-64-v1 CPU.** Verified, not assumed:
it pulled and ran `alpine` successfully. So anything too new for Debian 13 can
run here anyway, without touching the host.

`distrobox 1.8.1.2` goes further: it runs another distribution's **userland** in
a container, tightly integrated with your home directory.

```bash
distrobox create --name ubuntu --image docker.io/library/ubuntu:26.04
distrobox enter ubuntu
```

That gives you Ubuntu 26.04's packages on this machine **without reinstalling
anything and without touching the boot path** — which matters, because the boot
path on this machine is the fragile part (see §13). If something is only
packaged for Ubuntu, this is how to run it.

`buildah` and `skopeo` are installed for building and moving images.

**Docker 26.1.5** and **Docker Compose 2.26.1** are also installed and running,
because most instructions on the internet say `docker run`, not `podman run`.
Verified by actually running a container. Podman remains available and is the
safer of the two — it needs no daemon and no privileged group.

> **Being in the `docker` group is equivalent to being root.** Anyone who can
> talk to the Docker daemon can mount the host filesystem into a container and
> write anywhere. That is a property of Docker, not a misconfiguration here.
> Either use `sudo docker`, or use `podman`, which does not have this problem.

#### What a container can and cannot rescue

This is the part that decides whether a given piece of software will work here,
and it is easy to get backwards. **A container shares the host's kernel and the
host's CPU.** It swaps the *userland* — libraries, package versions, distro —
and nothing else. Measured on this machine:

| | host | inside a container |
|---|---|---|
| `sse4_2`, `avx`, `avx2` | absent | **still absent** |
| glibc | 2.41 | 2.39 in `ubuntu:24.04` |

So:

- **Wrong library or distro version → Docker fixes it.** Anything built for
  Ubuntu, a newer Python, a newer Node, an old PHP: run it in a container.
- **Needs AVX or SSE4.2 → Docker cannot help.** The instructions are not there
  to be virtualised. `mongodb` 5 and later, and official Ollama builds, require
  AVX and will fail inside a container exactly as they fail outside it.

Worth knowing: Debian 13's glibc 2.41 is *newer* than Ubuntu 24.04's 2.39. The
host is not the old part of this machine — the CPU is.

#### Which container-only applications actually run here

Tested on this machine, not inferred. Several popular applications ship as
containers and are genuinely painful to install any other way; the question was
whether a 2006 CPU can run them. It can:

| Application | What it is | Result |
|---|---|---|
| **Open WebUI** | ChatGPT-style web interface | **does NOT run** — see below |
| **Home Assistant** | home automation | **runs** — container stays up |
| **Vaultwarden** | Bitwarden-compatible password manager | **runs** — exits only because it refuses to start without a persistent volume, which is a safety feature |
| **Paperless-ngx** | document archive with OCR | **runs** — exits only because it wants Redis and Postgres alongside it |
| `mongo:7` | database — *deliberate negative control* | **fails: exit 132 (SIGILL)** |

MongoDB prints the reason itself before dying:

```
WARNING: MongoDB 5.0+ requires a CPU with AVX support, and your current
system does not appear to have that!
```

That is the boundary, demonstrated rather than assumed. **Exit code 132 is
128+4, meaning SIGILL** — worth memorising, because it is the signature of a
too-new binary on this CPU and it looks like an ordinary crash otherwise.

> ### Open WebUI does not work here, and the reason is worth knowing
>
> An earlier version of this table said Open WebUI runs. That was wrong, and
> the mistake is instructive: the container was still alive 45 seconds in, so a
> short smoke test called it a pass. It crashes *later* in startup, after the
> database migrations, with **exit 132 — SIGILL**.
>
> The cause is **NumPy**. Its x86-64 builds require SSE4.2, which this 2006
> Xeon does not have, and `open_webui/config.py` imports `chromadb`
> unconditionally, which imports NumPy. So it dies before serving anything.
>
> None of the obvious escapes work, all tried here:
>
> | Attempt | Result |
> |---|---|
> | `VECTOR_DB=qdrant`, `RAG_EMBEDDING_ENGINE=openai` | still 132 — the import is unconditional |
> | NumPy 1.26 / 2.0 / 2.1 wheels | all 132 |
> | NumPy built from source, `-Dcpu-baseline=min` | still 132 — "min" already means x86-64-v2 |
> | NumPy from source, `sse2` baseline, `allow-noblas` | still 132 |
>
> NumPy 2.x treats SSE4.2 as a hard floor on x86-64, not a tunable default.
> `torch`, `onnxruntime`, `sentence_transformers` and `faster_whisper` in that
> image fail the same way.
>
> **The way to have this interface anyway:** run Open WebUI on a modern
> computer and point it at *this machine's* gateway, which now speaks the
> OpenAI dialect (below). The old machine keeps the keys and does the talking;
> the modern one only draws the page.

None of these images is retained on the machine — they were pulled, tested and
removed again, so the results above are evidence rather than an installation.
Pull whichever one you want:

```bash
docker pull vaultwarden/server                       # ~290 MB
docker pull ghcr.io/paperless-ngx/paperless-ngx      # ~2.5 GB
docker pull ghcr.io/home-assistant/home-assistant    # ~2.4 GB
```

Each needs its own volumes, and Paperless needs a `docker compose` stack with
Redis and Postgres beside it.

### Cockpit — system administration in a browser

```
http://<this-machine>:9090/
```

Log in with the `macpro` account. Manage services, storage, networking, logs,
updates and terminal sessions from a browser, on any device. For someone new to
Linux this is the difference between learning `systemctl` and clicking a switch.

Not to be confused with the **AI Cockpit** on port 3000 — different thing, same
unfortunate word. This one is Red Hat's system admin console, from Debian.

### Snapshots — undo a bad change

`timeshift 24.06.6` in rsync mode, with a baseline snapshot of the fully
configured system:

```bash
sudo timeshift --list                       # what exists
sudo timeshift --create --comments "before I try something"
sudo timeshift --restore                    # roll back
```

**A snapshot is not a backup.** These live on the same disk, so they protect
against a bad configuration change, not against the disk dying. Backups still
belong on external media — see [DISK-HEALTH-AND-BACKUP.md](DISK-HEALTH-AND-BACKUP.md).

### Desktop applications — current versions, via Flatpak

Debian's own packages are stable but old. Flatpak carries **current upstream
releases** and keeps them isolated from the system, so a modern Firefox cannot
drag in libraries that break everything else. All four were launched and
confirmed to draw a real window on this CPU, not merely to install:

| App | Version | Launch |
|---|---|---|
| Firefox | 154.0 | Applications menu, or `flatpak run org.mozilla.firefox` |
| LibreOffice | 26.2.5.2 | documents, spreadsheets, presentations |
| VLC | 3.0.23 | plays essentially any video or audio file |
| GIMP | 3.2.4 | image editing |

Debian's older Firefox ESR is still installed and still works; the Flatpak one
is the current release. Either is fine.

```bash
flatpak list --app            # what is installed
flatpak update                # update all of them
```

> **`dbus-x11` and `xdg-desktop-portal-gtk` are not optional here.** Without
> them a Flatpak app cannot open the file-chooser dialog, so "Open…" in
> LibreOffice silently does nothing, and **GIMP aborts on startup** while its
> icon loader fails. Both packages are installed for exactly this reason. If
> Flatpak apps ever start misbehaving after a reinstall, check these first.

### Desktop icons

The icons on the desktop are grouped in four columns:

| Column | Holds |
|---|---|
| 1 | **Start Here**, **AI Terminal**, **AI Cockpit**, and the printable guide |
| 2 | Firefox, LibreOffice, VLC, GIMP, OpenShot |
| 3 | VS Code, Files, Terminal |
| 4 | Home, File System, Trash |

Labels are deliberately one word. Desktop icon labels truncate at about twelve
characters, so "GIMP — Photo Editor" renders as "GIMP — Pho…", which is worse
than the bare name. The longer description lives in the hover tooltip.

Positions are stored in
`~/.config/xfce4/desktop/icons.screen0.yaml`. **xfdesktop rewrites that file
when it exits**, so anything edited while it is running is discarded — stop it
first, edit, then start it again. Dragging icons by hand works fine and is the
normal way to change this.

### Wi-Fi — now works, and did not before

The machine has a **Broadcom BCM4321** card that was doing nothing at all: the
`b43` driver loaded and then failed, because its firmware is not redistributable
and `firmware-b43-installer` — the package that used to fetch it — **no longer
exists in Debian 13**.

The route that works is the proprietary `wl` driver:

```bash
sudo apt install linux-headers-$(uname -r) broadcom-sta-dkms
```

**The kernel headers are the part that is easy to miss.** Without them DKMS
reports the module as merely `added` rather than `installed`, `modprobe wl`
says "module not found", and it looks like a driver incompatibility rather than
a missing build dependency.

Verified working: the interface appears as **`wls5`**, the radio scans and finds
networks, and NetworkManager manages it — so Wi-Fi can be joined from the normal
desktop menu. `broadcom-sta-common` blacklists `b43`, `bcma`, `ssb` and
`brcmsmac` so the right driver claims the card at boot.

> Wired Ethernet is still the better choice for a desktop that never moves, and
> is what the machine uses today. Wi-Fi is there for when the cable is not.

### Sharing files with other computers

Two different tools, for two different jobs.

**Samba — a shared folder on the network.** Good for dragging a file across
once. From a Mac, Finder → Go → Connect to Server:

```
smb://macpro/share
```

From Windows: `\\macpro\share`. The folder is `/srv/share` on this machine.

**Samba keeps its own password, separate from the Linux login.** Nothing works
until the owner sets one — deliberately left undone, because nobody should
receive a machine with a password somebody else chose:

```bash
sudo smbpasswd -a macpro
```

**Syncthing — a folder that stays in sync.** Better for ongoing work: pick a
folder here and a folder on a laptop, and they mirror each other continuously in
both directions. No cloud account, no subscription, and the files never leave
your network.

It runs as the `macpro` user (its whole model is "this user's folders"; a system
service would sync as root). Open its interface on the machine at:

```
http://localhost:8384
```

To pair with a Mac or PC: install Syncthing there, then swap Device IDs between
the two web interfaces and choose a folder to share. Once paired, dropping a
file in the folder on either machine makes it appear on the other. Both sides
have full read/write access — it is a sync, not a one-way copy.

Ports 22000 (transfer) and 21027 (finding other devices) are open on the LAN.

### Printing and scanning

CUPS is running, with drivers for the common families (Gutenprint covers most
Epson/Canon, `printer-driver-escpr` newer Epson, `hplip` HP) and **network
printer discovery is live** via Avahi — so a printer on the same network is
usually found without being told anything about it.

Add a printer through **Settings → Printers** (`system-config-printer`), or in a
browser at `http://localhost:631`. Scanning is **Document Scanner**
(`simple-scan`).

mDNS discovery already had its firewall hole (UDP 5353), so nothing needed
opening. Printing is outbound, so it needs no inbound rule at all.

### Sound

Works, and was tested rather than assumed: the onboard **ALC889A** codec is
driven by PulseAudio 17, Master unmuted, and a test tone played cleanly through
both channels. Volume lives in the panel, or:

```bash
alsamixer                 # arrow keys; M mutes
speaker-test -c 2 -t sine -f 440 -l 1
```

PipeWire is deliberately **not** installed. The log shows
`xdg-desktop-portal: can't load config client.conf` because the portal looks for
PipeWire and does not find it. That warning is harmless — it affects screen
*sharing*, not audio — and replacing a working sound stack on a nineteen-year-old
machine buys nothing.

### Desktop look — Arc-Dark and Papirus

| Setting | Value |
|---|---|
| Window and widget theme | Arc-Dark |
| Icons | Papirus-Dark |
| Interface font | Noto Sans 10 |
| Monospace font | JetBrains Mono 10 |
| Font rendering | antialiased, slight hinting, RGB subpixel order |

Change any of it in **Settings → Appearance**, or from a terminal:

```bash
xfconf-query -c xsettings -p /Net/ThemeName -s Arc-Dark
```

> **If a setting appears to do nothing, restart the settings daemon**, not the
> machine. GTK reads the theme from the XSETTINGS manager, and if `xfsettingsd`
> is not publishing, every app silently falls back to the default Adwaita look
> while `xfconf-query` cheerfully reports the theme you asked for. That
> mismatch cost real time to diagnose here:
>
> ```bash
> xfsettingsd --replace &
> ```
>
> To see what applications *actually* resolved, rather than what was requested:
>
> ```bash
> python3 -c "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk; \
> Gtk.init([]); w=Gtk.Window(); w.realize(); \
> print(w.get_style_context().lookup_color('theme_bg_color')[1].to_string())"
> ```
>
> A dark colour means the dark theme really is loaded. Verified to survive a
> full logout and login.

### A second, lighter desktop: LXDE

**LXDE** is installed alongside Xfce and offered at the login screen. On a
machine drawing 2560×1440 with no working GPU acceleration, LXDE is noticeably
lighter. Choose it from the session menu on the login screen — the small icon
near the username — then log in as usual. Xfce remains the default.

Openbox is also listed there; it is the bare window manager underneath LXDE,
with no panel or desktop icons. Useful, but not somewhere to start.

### Video editing

`openshot-qt 3.1.1` — timeline video editor, from Debian. Paired with
**`ffmpeg 7.1.5`** for anything scriptable:

```bash
ffmpeg -i input.mov -c:v libx264 -crf 20 output.mp4
```

### Newer packages when they are needed: backports

`trixie-backports` is enabled but **nothing is installed from it**, which is the
correct state: backports are for when you specifically need a newer version, not
a source to upgrade everything from.

```bash
apt list -a <package>                                  # see if backports has it
sudo apt install -t trixie-backports <package>         # take the newer one
```

### Hardening and housekeeping

| | |
|---|---|
| `fail2ban` | bans repeated failed SSH logins. SSH is open to the LAN, so this matters. |
| `lynis` | security audit — run `sudo lynis audit system` for a report |
| `needrestart` | restarts services after an update. Desktop pop-ups are turned off in `/etc/needrestart/conf.d/90-no-desktop-nag.conf` — one per `apt` run buried the screen in red warnings. Run `needrestart` by hand to see what is pending. |
| `fwupd` | firmware updates where a vendor provides them; it does enumerate this Mac's devices |
| `unattended-upgrades` | security patches apply themselves |

### Also available

`syncthing` (installed, not enabled — file sync between machines), `zsh` +
`zoxide`, `plocate`, `wmctrl` and `xdotool` (script the desktop from a terminal).

## Log noise that is not worth chasing

A sweep of the journal turned these up. They are recorded so nobody spends an
afternoon on them twice.

| Message | Verdict |
|---|---|
| `i5k_amb ... failed with error -16` | The FB-DIMM temperature sensor cannot claim its I/O region (`-16` is `EBUSY`) because the firmware holds it. `acpi_enforce_resources=lax` on the kernel line would likely fix it and would give per-DIMM temperatures — genuinely useful on a machine with FB-DIMM history. **Not applied**, because this machine has an unexplained intermittent boot fault and adding a kernel parameter would confound that investigation. Worth revisiting once the boot fault is understood. |
| `pw.conf: can't load config client.conf` | PipeWire is not installed; the portal looks for it anyway. Audio is unaffected — see Sound above. |
| `alsa-restore.rules: GOTO has no matching label` | A genuinely broken rule Debian ships, ten errors per boot. Overridden in `/etc/udev/rules.d/90-alsa-restore.rules` rather than editing the shipped file, which an upgrade would revert. |
| `Unknown username "geoclue"` | Location service partially installed. Harmless. |
| `pam_wtmpdb ... SQLITE_DONE: 8` | Logout time not recorded, twice, at shutdown. The database is healthy and writable and `last` works. A shutdown race; ignore. |
| `coretemp: Using relative temperature scale` | This CPU has no absolute temperature reference, so readings are approximate. Nothing to fix. |
| `DOCKER_OPTS` / `smartd_opts` unset | systemd noting an unset optional variable. Cosmetic. |
| `hid-generic / apple: unknown main item tag 0x0` | The Apple keyboard reports a descriptor field Linux does not recognise. The keyboard works. |

## Should this machine have a mail system?

**No, and it deliberately does not.** No postfix, exim, mailx or msmtp.

The usual argument for one is that system tools mail `root` when something goes
wrong. That argument fails here twice over: a mail transport is another service
to keep patched, and **a beginner would never read root's mailbox anyway**. The
warning would be as invisible as it was before.

So the things that used to mail instead report where a person will actually look:

| | |
|---|---|
| Failing disk | writes `DISK-WARNING-READ-ME.txt` to the desktop and pops a notification — see DISK-HEALTH-AND-BACKUP.md |
| Security updates | `unattended-upgrades` keeps its own log; `ai check` reports it |
| Anything else | `journalctl -p err -b` shows this boot's errors |

If you later want mail off this machine — to a real address rather than a local
mailbox — `msmtp` plus an SMTP account is the small answer, and does not involve
running a mail server. That is a deliberate choice for the owner, not a default.

## The firewall, corrected

`/etc/nftables.conf` was found to be **missing the DHCP rule** that this
documentation had described for weeks — the corrected version had been written
to the repository but never installed on the machine. Without it the machine
loses its address on the next cold boot, which is indistinguishable from a dead
machine.

Now deployed and verified, with 9090 added for Cockpit:

```
udp dport 68 accept          # DHCPv4 -- reply is a different tuple, so
udp dport 546 accept         # `ct state established` does NOT cover it
tcp dport { 22, 3000, 8081, 8443, 9090, 24800 }   from 192.168.0.0/16
```

Applied with a 90-second auto-rollback in case it locked out SSH. It did not.

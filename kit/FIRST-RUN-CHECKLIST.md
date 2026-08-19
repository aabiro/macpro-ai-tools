# First-run checklist — for the new owner

Everything on this machine is installed, running and tested. Every credential is
deliberately blank.

**No accounts belonging to the previous owner are attached to this machine.** No
API keys, no Tailscale identity, no cloud storage credentials, no signed-in
sessions. That is intentional: the machine was built and repaired remotely, then
stripped of every account before handover. The steps below are yours to complete
with your own credentials.

Until you do, the AI tools start up and then politely refuse to do anything —
which is the correct behaviour, not a fault.

Work top to bottom. Each step says how to prove it worked.

**Do all of these on day one.** They are not polish — until they are done the
machine has no AI capability, no remote access, and no backups.

| # | Step | Needs |
|---|---|---|
| 0 | **Revoke build-time access** | nothing — do this before anything else |
| 1 | **Model API keys** | your provider accounts |
| 2 | **code-server password** | already generated; change it if you like |
| 3 | **Tailscale** | your own tailnet |
| 4 | **Ports / firewall** | nothing — read before opening anything |
| 5 | **Offsite backups to B2** | your own bucket |

---

## 1. Model API keys — required

Nothing AI-related functions without this. One file feeds both the gateway and
the web console, so there is a single place to rotate keys.

```bash
sudo nano /etc/ai-cockpit/env
```

Fill in whichever providers you have. Blank ones are simply reported as
unconfigured; they do not break anything.

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

Then restart and check:

```bash
sudo systemctl restart ai-gateway cockpit-web
curl -s localhost:8081/health
```

**Proof it worked:** `providers_configured` lists your providers instead of `[]`.

```json
{"status":"ok","providers_configured":["anthropic","gemini"], ...}
```

The file is `root:aigw` mode 0640 — readable by the two services and nobody
else. Keep it that way.

### The CLI tools read the same keys

`claude`, `gemini` and `codex` each expect their key in your shell environment,
which is separate from the services above. Add to `~/.bashrc`:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=...
```

The `g5-*` tools do **not** need this — they go through the gateway and use its
keys. That is the whole point of them, and it is why they work on Lion.

## 2. code-server password — already set

A random password was generated at install. Read it:

```bash
sudo grep password: /home/macpro/.config/code-server/config.yaml
```

Then open `http://<machine-ip>:8443/`. Change it by editing that file and
running `sudo systemctl restart code-server`.

## 3. Tailscale — do this early

`tailscale` is installed and `tailscaled` runs at boot, but the machine holds
**no identity**: it was never registered, and the state file was deleted before
handover so no previous owner's tailnet is attached. `tailscale status` says
`Logged out.` — that is the shipped state, and it is deliberate.

Register it to **your own** tailnet. This is worth doing on day one: it is how
you reach the machine without opening a single router port, and it is the only
sane way to expose the cockpit and editor beyond the LAN. Run this on the Mac
Pro:

```bash
sudo tailscale up --hostname=macpro-g5
```

It prints a `https://login.tailscale.com/a/...` URL. **Open that URL in a
browser on any machine where you are already signed in to Tailscale** — your
laptop is easiest. The browser approves it; the Mac Pro does not need a browser
of its own.

**Proof it worked:**

```bash
tailscale status        # no longer "Logged out"
tailscale ip -4         # prints a 100.x.y.z address
```

### Then publish the services over HTTPS

Once on the tailnet, this gives real certificates with nothing to manage, and
nothing exposed to the public internet:

```bash
sudo tailscale serve --bg --https=443 http://127.0.0.1:3000    # cockpit
sudo tailscale serve --bg --https=8443 http://127.0.0.1:8443   # editor
tailscale serve status
```

They then answer at `https://macpro-g5.<your-tailnet>.ts.net/` from any device
on your tailnet.

**Do not port-forward these from your router instead.** The gateway has no
authentication beyond a private-range IP check, and its own source file says so.
The nftables ruleset and the tailnet are what keep it safe.

## 4. Ports, and what is allowed to reach them

| Port | Service | Reachable from |
|---|---|---|
| 22 | SSH | LAN + tailnet |
| 3000 | cockpit web console | LAN + tailnet |
| 8081 | AI gateway | LAN + tailnet |
| 8443 | code-server (editor) | LAN + tailnet |
| 41641/udp | Tailscale | anywhere (by design) |

Everything else is dropped. The ruleset lives in `/etc/nftables.conf`; to open
another port, edit the `tcp dport { ... }` set and run `sudo nft -f
/etc/nftables.conf`.

To check what is actually listening versus what you think is:

```bash
sudo ss -lntp
sudo nft list ruleset
```

## 5. Revoke the remote access used to build this — do before handover

Passwordless sudo and an SSH key were added so the machine could be repaired
remotely. **The rule exists in two places**, and a broken sudoers file locks
everyone out, so run the check at the end:

```bash
sudo rm /etc/sudoers.d/90-macpro-automation
sudo sed -i '/^macpro ALL=(ALL) NOPASSWD:ALL$/d' /etc/sudoers
sudo visudo -c
sed -i '/aaryn.alexander@gmail.com/d' ~/.ssh/authorized_keys
```

`macpro` stays in the `sudo` group and will be asked for a password — the normal
Debian arrangement.

## 6. Optional: offsite backups

`restic` is not installed. If you want encrypted offsite snapshots, the project
already has Backblaze B2 credentials for the `ca-east-006` region. Sketch:

```bash
sudo apt install restic
export B2_ACCOUNT_ID=...  B2_ACCOUNT_KEY=...
restic -r b2:your-bucket:macpro init
restic -r b2:your-bucket:macpro backup /home/macpro/projects
```

Left out deliberately — it needs bucket credentials and a decision about what is
worth backing up, both of which are the owner's call.

## 7. Where to read next

| | |
|---|---|
| Everything installed, ports, MCP servers | [AI-STACK.md](AI-STACK.md) |
| Black screen, boot problems, the radeon fault | [LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) |
| Newer macOS, CPU and GPU upgrades | [HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md) |

All three are also on the machine at `/usr/local/share/doc/macpro/kit/`.

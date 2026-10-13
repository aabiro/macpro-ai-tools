# The AI Cockpit — Mac Pro 1,1

Welcome to your "new" 2006 Mac Pro. This document is the one thing you need to
read. It is written to be followed by someone who has never used this machine
before.

---

## 1. What this machine is

| | |
|---|---|
| Model | Mac Pro 1,1 (2006) — the aluminium tower that shares its case with the Power Mac G5 |
| Processors | 2 × Intel Xeon 5150 "Woodcrest", 2.66 GHz — 4 cores total |
| Memory | 6 GB DDR2 FB-DIMM, ECC |
| Disks | 2 × 1 TB mechanical drives |
| Operating system | Mac OS X 10.7.5 Lion |

It is a genuinely capable machine for writing, browsing local files, audio work,
and as a quiet always-on box. It has one hard limitation, described next.

---

## 2. The one thing that is broken, and why

**This Mac cannot connect to almost any modern website or online service.**

It is not a virus, and nothing is misconfigured. Lion ships with an encryption
library from 2010 (OpenSSL 0.9.8). Essentially every site and API on the modern
internet now requires TLS 1.2 or newer, which this version cannot speak. The
connection fails before it starts:

```
$ curl -o /dev/null -w '%{http_code}' https://api.anthropic.com
000
```

`000` is not a website error. It means no connection happened at all.

Apple stopped supporting Lion in 2014, so this will never be fixed by an update.
You have three options, and you can use all of them:

1. **Use the AI Cockpit** (already installed). It routes through a small helper
   program on a newer computer. Covered in section 3.
2. **Install Linux** on the second drive. Modern OS, modern browser, full
   development environment. Covered in `docs/LINUX-STARTER-PACK.md`.
3. **Leave it as a vintage Mac.** It runs period software beautifully.

---

## 3. Getting the AI Cockpit working

The Cockpit lets you chat with AI models, get this machine's health explained,
and translate modern code so it builds here. It needs one helper program — the
**gateway** — running on any newer computer on your network (a laptop is fine).

```
   [ This Mac Pro ]  --plain HTTP-->  [ Your laptop ]  --modern TLS-->  [ AI service ]
     too old for TLS                    runs aigw.py                     
```

Your API key stays on your laptop. It is never copied to this Mac.

### Step 1 — copy the gateway to your modern computer

The file is on this Mac at:

```
/Users/Shared/ai-cockpit/gateway/aigw.py
```

Copy it to your laptop however you like — USB stick, or from your laptop run:

```bash
scp -o HostKeyAlgorithms=+ssh-rsa \
    <thismac>:/Users/Shared/ai-cockpit/gateway/aigw.py .
```

> The `HostKeyAlgorithms` flag is required. Modern SSH refuses Lion's older
> host key type unless you ask for it explicitly.

### Step 2 — get an API key

Pick one provider. Any single one is enough.

| Provider | Where to get a key | Env variable |
|---|---|---|
| Google Gemini | <https://aistudio.google.com/apikey> | `GEMINI_API_KEY` |
| Anthropic Claude | <https://console.anthropic.com/> | `ANTHROPIC_API_KEY` |
| OpenAI | <https://platform.openai.com/api-keys> | `OPENAI_API_KEY` |

Gemini currently has a free tier, which makes it the easiest starting point.

### Step 3 — run the gateway on your modern computer

Requires Python 3.7 or newer. Nothing to install — no pip, no packages.

```bash
export GEMINI_API_KEY=your-key-here
python3 aigw.py
```

It prints the address to use:

```
 Reach it at     : http://192.168.1.50:8081
```

Leave that window open. The gateway only runs while it is open.

### Step 4 — point this Mac at it

Back on the Mac Pro, in Terminal:

```bash
g5-config set gateway http://192.168.1.50:8081
```

(substitute the address the gateway printed). It will immediately test the
connection and send a live prompt.

### Step 5 — use it

```bash
cockpit
```

---

## 4. The commands

| Command | What it does |
|---|---|
| `cockpit` | Full-screen interface — chat, health, code porting, settings |
| `g5-config show` | Show current settings |
| `g5-config test` | Check the gateway and send a live test prompt |
| `g5-config set gateway <url>` | Point at your gateway |
| `g5-config set provider <name>` | `gemini`, `anthropic`, or `openai` |
| `g5-doctor` | Health report on this machine, explained in plain language |
| `g5-doctor --raw` | The raw readings, no AI, works with no network at all |
| `g5-assist "..."` | Describe what you want; get a shell command, confirm before it runs |
| `retro-port FILE` | Rewrite a source file so it builds on this machine |

If a command is not found, open a new Terminal window, or run:

```bash
source ~/.bash_profile
```

---

## 5. If something goes wrong

**"No AI gateway is configured yet"**
You have not done Step 4, or you are on a different user account. Run
`g5-config show`.

**"Could not reach the gateway"**
The gateway window on your laptop has been closed, the laptop is asleep, or the
laptop moved to a different network. Both machines must be on the same network.

**"The gateway is running but has no API keys"**
You started the gateway without setting the key in that same terminal window.
Set the key and start it again — the two commands must run in the same window.

**A model name error mentioning 404 / "no longer available"**
Providers retire model names every so often. Ask the gateway to use its own
current default:

```bash
g5-config unset model
```

**Everything is slow**
This is a 2006 machine and the AI reply must cross your network twice. Twenty
seconds is normal. The `--raw` health report is instant because it never leaves
the machine.

---

## 6. Health checks worth doing

This is a nineteen-year-old computer. Run this occasionally:

```bash
g5-doctor
```

The things that actually fail on this model, in order of likelihood:

1. **FB-DIMM memory.** These modules run extremely hot and are the most common
   failure. Symptoms: random freezes, kernel panics, or a memory slot showing a
   status other than OK.
2. **Power supply.** Symptoms: refusing to power on, or shutting off under load.
3. **Dust and thermal paths.** Nineteen years of dust. Worth opening the side
   panel and clearing it gently with compressed air.
4. **The mechanical drives.** Both are well past typical service life. `g5-doctor`
   reports their SMART status. **Do not keep the only copy of anything on this
   machine.**

---

## 7. Where everything lives

```
/Users/Shared/ai-cockpit/
├── README.md              this file
├── config.json            machine-wide settings
├── bin/                   the commands
├── gateway/
│   ├── aigw.py            copy this to your modern computer
│   └── README.md          gateway details
├── docs/
│   ├── LINUX-STARTER-PACK.md   installing Linux on the second drive
│   ├── HANDOFF.md              full technical handover notes
│   └── IMPLEMENTATION-PLAN.md  the phased build plan
└── *.py                   the programs themselves
```

Your personal settings live in `~/.g5ai.json` and override the machine-wide
`config.json`.

---

## 8. Second drive

The second 1 TB drive currently holds a volume named **Liferaft** — a complete
backup clone of this Lion system, made before the machine was handed over. It is
a safety net: if the main system is ever damaged, you can boot from it by holding
**Option** at startup.

Once you are confident the machine works, that drive is the natural place to
install Linux. See `docs/LINUX-STARTER-PACK.md`.

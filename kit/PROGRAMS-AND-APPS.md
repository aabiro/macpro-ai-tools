# Everything installed, and what it is for

A complete list of what is on this machine. If you only want to get started,
read [QUICKSTART.md](QUICKSTART.md) instead — this page is a reference, not a
tutorial.

Groups are ordered by how likely you are to want them.

---

## On the desktop

Eleven icons, arranged in columns. These are the things worth using first.

| Icon | What it is |
|---|---|
| **Start Here** | A page of clickable links explaining the machine. Opens by itself the first time you log in. |
| **AI Cockpit** | Chat with an AI and see the machine's health, in one window. |
| **AI Terminal** | A terminal window with `ai` already run, so it tells you what to do. |
| **Firefox** | Web browser. Current version, kept updated. |
| **Files** | Browse your files and folders. |
| **VS Code** | A full code editor. Also used for the Lion work below. |
| **LibreOffice** | Documents, spreadsheets, presentations. Opens Word and Excel files. |
| **GIMP** | Photo and image editing. |
| **OpenShot** | Video editing. |
| **VLC** | Plays essentially any video or audio file. |
| **Terminal** | The plain command line. |

## Everyday applications

| Program | What it does |
|---|---|
| Firefox / Firefox ESR | Two browsers. Firefox is current; ESR is the long-term-support build, kept as a fallback. |
| LibreOffice (Writer, Calc, Impress, Draw, Base, Math) | The full office suite. |
| GIMP | Image editing. |
| OpenShot | Video editing. |
| VLC, MPlayer | Video and audio playback. |
| Quod Libet / Ex Falso | Music player and audio tag editor. |
| Atril | PDF and document viewer. |
| Ristretto, GPicView | Image viewers. |
| Xarchiver | Open and create zip, tar, 7z archives. |
| Mousepad, Vim | Simple text editor, and the classic terminal editor. |
| Galculator | Calculator, including scientific mode. |
| Dictionary | Look up words. |
| Deluge | BitTorrent client. |
| Xfburn | Burn CDs and DVDs. |
| Document Scanner, XSane | Use a scanner. Printing and scanning are set up and tested. |
| Character Map | Insert accented and special characters. |
| Screenshot | Capture the screen or a single window. |

## The AI tools

The command-line tools all live on `PATH`, so you can just type them.

| Command | What it does |
|---|---|
| `ai` | **Start here.** Looks at the machine and tells you what to do next. |
| `ai setup` | Switches the AI on: gets a key, tests it against the real service, saves it only if it works. |
| `ai check` | Plain-English report of whether anything is wrong. |
| `ai fix` | Repairs what is safe to repair. Never touches your files. |
| `ai chat` | Talk to an AI in the terminal. |
| `ai undo` | Puts back the last change `ai` made. |
| `ai-session` | Records a terminal session so it can be replayed or shared. |
| `claude` | Anthropic's Claude Code CLI — an AI that can read and edit code. |
| `codex` | OpenAI's Codex CLI. |
| `gemini` | Google's Gemini CLI. Gemini has a free tier, so this is the cheapest starting point. |
| `aider` | AI pair-programming in a git repository. |
| `cockpit` (AI Cockpit) | The graphical version of all of the above. |

In VS Code, the **Claude Code** and **ChatGPT** extensions are installed, along
with **Gemini Code Assist**. They work on the open folder and can run commands.

### The gateway

`ai-gateway` is a small service on this machine that performs modern HTTPS on
behalf of programs that cannot. It matters because **this machine's Mac OS X
side cannot do TLS 1.2 at all** — see [AI-STACK.md](AI-STACK.md).

It is running as a service and listens on port 8081. It holds no API keys until
you add one with `ai setup`.

## Running the old Mac OS system

The second hard disk still has Mac OS X 10.7.5 Lion on it. You can run it as a
virtual machine **while Linux is running**, which is how you would inspect or
fix it without rebooting.

| Command | What it does |
|---|---|
| `lion-vm start` | Boot Lion as a VM. Ready in about a minute. |
| `lion-vm stop` | Shut it down cleanly. |
| `lion-vm status` | Is it running? How big is its overlay? |
| `lion-vm snapshot` / `restore` | Save the VM's state, or roll back to the saved one. |
| `lion-vm screenshot` | Capture the VM's screen. |
| `lion` | Run a command inside Lion, as root. `lion` alone gives a shell. |
| `lion-cp` | Copy files in or out of the VM. |
| `lion-run FILE` | Run a file that lives in Lion, inside Lion. |
| `lion-mount` | Make Lion's files appear at `/mnt/lion-live` (also `~/Lion`). |
| `lion-provision` | One-off: install the AI cockpit inside the VM. Already done. |
| `lion-setup-editor` | One-off: wire VS Code up to the Lion project. Already done. |

The VM and the folder come up automatically at start-up, so normally you do not
have to run any of this.

**The failing disk is never written to.** It is the read-only backing file of a
copy-on-write overlay. Full explanation: [LION-VM.md](LION-VM.md).

## Health, backup and recovery

| Command / program | What it does |
|---|---|
| `macpro-doctor` | Full health check of the machine in one command. |
| `macpro-telemetry` | Collects the numbers `macpro-doctor` reads. Runs every 5 minutes. |
| `backup-now` | Copies your files to a USB drive. **Refuses to write to the internal disks** — it checks the target is really USB first. |
| Timeshift | Snapshots of the system, so a bad change can be rolled back. |
| Disks / Disk Management | Format and mount drives. |
| `smartctl` | Reads a disk's own health data. `sudo smartctl -a /dev/sda` |
| Task Manager, btop++, Htop | See what is using the processor and memory. |
| Sensor Viewer | Temperatures and fan speeds. |

Backups run daily by themselves, but only if a drive labelled `MACPRO-BACKUP`
is plugged in. Without one, nothing happens and nothing complains. If a disk
starts failing, a file appears on your desktop saying so.

## Web interfaces

Open these in Firefox on the machine.

| Address | What it is |
|---|---|
| `http://localhost:3000` | **AI Cockpit** — the web version of the AI tools and the health view. This is what the desktop's AI Cockpit icon opens. |
| `https://localhost:9090` | **Cockpit** — manage the whole machine in a browser: services, logs, storage, updates, a terminal. |
| `http://localhost:8443` | **Code Editor** — VS Code in the browser, if you prefer that to the desktop app. |
| `http://localhost:8384` | **Syncthing** — sync files with your other computers. |
| `http://localhost:8081/health` | The AI gateway's status. |
| `http://localhost:5901` | Not a web page — this is the VNC port for the Lion VM's screen, for a VNC viewer. |

## Networking and sharing

| Thing | What it does |
|---|---|
| Samba share `\\<this-machine>\share` | A shared folder at `/srv/share`, reachable from a Mac or Windows PC. Requires the `macpro` password; guests are refused. |
| Syncthing | Keeps folders in sync with your other machines, without a cloud service. |
| Avahi | Lets other computers find this one by name rather than IP address. |
| nftables firewall | Blocks everything except the ports listed above. |
| fail2ban | Bans an address that repeatedly fails to log in over SSH. |
| Advanced Network Configuration | Wi-Fi and wired settings. Wi-Fi works. |

## Development tools

| Thing | What it does |
|---|---|
| VS Code | The main editor. Extensions for Python, YAML, TOML, CSV, shell checking, git, and three AI assistants. |
| Python 3.13 + IDLE | Current Python, and its simple built-in editor. |
| `uv` / `uvx` | Very fast Python package installer. Prefer it to `pip`. |
| Node.js 24 | JavaScript runtime, with `npm`. |
| `git`, GitLens | Version control, plus a VS Code extension that visualises history. |
| Docker | Runs containers. Useful for software too new to install directly on Debian 13 — see the container section of [AI-STACK.md](AI-STACK.md). No images are currently downloaded. |
| `bat`, `fd`, `ripgrep` | Better `cat`, `find` and `grep`. |
| `build-essential` | C/C++ compiler and make, for building software from source. |
| Jupyter | Notebooks, via the VS Code extension. |

## Agent tools (MCP servers)

These let an AI assistant read and act on this machine directly, rather than
asking you to paste output. Nine are registered and all nine connect.

| Server | What the AI can do with it |
|---|---|
| `macpro-health` | Read hardware health: telemetry, SMART, ECC memory errors. |
| `macpro-journal` | Read boot and service logs. |
| `macpro-apt` | Query installed and available packages. |
| `macpro-lion` | **Run and control Mac OS X Lion in the VM** — 13 tools, including running commands, reading and writing files, and starting or stopping the VM. |
| `filesystem` | Read and write files under `~/projects`. |
| `git` | Inspect repositories. |
| `fetch` | Retrieve a web page. |
| `memory` | Remember things between sessions. |
| `time` | Current time and time-zone conversion. |

Check them with `claude mcp list`. The health, journal and apt servers are
read-only by design. The lion server can change things, but only inside the VM.

## System administration

| Program | What it does |
|---|---|
| Synaptic, Software | Install and remove programs, with a window rather than commands. |
| Users and Groups | Add or remove user accounts. |
| Session and Startup | Choose what runs when you log in. |
| Appearance, Customize Look and Feel | Themes and fonts. Set to Arc-Dark with Papirus icons. |
| Display / Monitor Settings | Resolution and multiple monitors. |
| Time and Date | Clock and time zone. |
| Default Applications | Which program opens which file type. |
| Lynis | Security audit. Run it as root: `sudo lynis audit system` |
| Setup Hot Keys, Keyboard | Keyboard shortcuts. |

## What is deliberately not installed

| | Why |
|---|---|
| Open WebUI | Needs NumPy, which requires SSE4.2. This 2006 processor does not have it, and no build works around that. |
| Chromium / Chrome | Firefox works and is lighter on a machine drawing everything with the processor. |
| A local large language model | Measured at roughly one word every few seconds. It works, but it is too slow to be useful. Details in [AI-STACK.md](AI-STACK.md). |
| Docker images | None are downloaded, to save disk. `docker pull` when you need one. |

---

Everything above is on the machine at `/usr/local/share/doc/macpro/kit/`.
Related reading:

| | |
|---|---|
| Getting started in five steps | [QUICKSTART.md](QUICKSTART.md) |
| Day one in detail | [NEW-OWNER-START-HERE.md](NEW-OWNER-START-HERE.md) |
| Why each AI piece exists | [AI-STACK.md](AI-STACK.md) |
| Running the old Mac system | [LION-VM.md](LION-VM.md) |
| Using both systems together | [USING-BOTH-SYSTEMS.md](USING-BOTH-SYSTEMS.md) |
| The failing disk, and backups | [DISK-HEALTH-AND-BACKUP.md](DISK-HEALTH-AND-BACKUP.md) |
| Black screens at start-up | [LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) |

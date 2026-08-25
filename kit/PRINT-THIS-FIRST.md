# Mac Pro — start here

**Print this and keep it with the machine.** It covers everything from pressing
the power button to having a working AI assistant. You do not need to know
anything about Linux, programming or AI.

Two systems are installed. Both work. You choose at power-on.

| | |
|---|---|
| **Debian Linux** | the modern side. AI tools, web browser, code editor. |
| **Mac OS X Lion** | the original 2006 system, with the previous owner's files. |

---

## 1. Power on

Press the power button once. Wait.

**If you see a desktop with a teal background — you are done, skip to step 3.**

**If the screen stays black for more than two minutes**, that is a known fault
with a known fix. Go to step 2.

## 2. Choosing which system starts

Hold the **Option** key (⌥, next to the spacebar) **before** you press power,
and keep holding it until icons appear.

You will see up to three icons:

```
   [ Lion ]        [ EFI Boot ]         [ EFI Boot ]
   silver           SILVER               ORANGE
   Mac OS X         Debian Linux         USB stick, if inserted
```

- **Silver "EFI Boot"** — Debian Linux. **This is the normal choice.**
- **"Lion"** — the old Mac system.
- **Orange** — only appears with a USB stick in. Ignore it.

Click the silver **EFI Boot**, then press Return.

A black-and-white menu appears. The top line is already selected:

```
> Debian GNU/Linux (normal)
  Debian - repair filesystem (forced fsck)
  Debian - emergency shell
  ...
```

Press **Return**. Wait up to two minutes.

**If that fails, come back and pick the second line** — "repair filesystem".
It checks the disk for damage and takes a few minutes longer. It is safe.

## 3. Logging in

Username: **macpro**
Password: **supplied separately with this machine**

## 4. Switch the AI on — the only setup step

Open a **Terminal** window (the black icon in the bar at the bottom of the
screen), then type this and press Return:

```
ai setup
```

It will ask which AI provider you want, show you the web page to sign up on, and
ask you to paste the key it gives you. It then **tests the key before saving
it** — if the key is wrong it tells you why and changes nothing.

Google Gemini has a free option and is the easiest place to start.

That is the whole setup. Everything else is already installed.

### Getting the key to paste — step by step

You need an account with an AI provider, and a "key" from it. A key is a long
password that lets a program use the AI on your behalf. It is **not** your
account password, and it is tied to money, so read the cost notes before
starting.

**The short version, for the free one:**

1. On any computer, go to **aistudio.google.com/apikey**
2. Sign in with a Google (Gmail) account — make one there if you have none
3. Click **Create API key** and copy the long string starting `AIza`
4. On this machine, run `ai setup`, choose Google Gemini, and paste it
   — paste with **Ctrl+Shift+V**; plain Ctrl+V does not work in a Terminal
   — you will not see the key appear as you paste; that is normal

**The full guide** — Anthropic, OpenAI and GitHub as well, what each costs, how
to set a spending limit, how to sign in to the editor extensions, and how to
recover if a key leaks — is on this machine at:

```
/usr/local/share/doc/macpro/kit/ACCOUNTS-AND-SIGN-IN.md
```

Read it with `glow` for a nicely formatted version:

```
glow /usr/local/share/doc/macpro/kit/ACCOUNTS-AND-SIGN-IN.md
```

**No key is included with this machine, and no previous owner's account is
attached to it.** Until you add one, the AI tools start up and politely refuse
to do anything. That is correct behaviour, not a fault.

## 5. The only commands worth remembering

Type these in a Terminal:

| Type this | What happens |
|---|---|
| `ai` | tells you what to do next |
| `ai setup` | switch the AI on (step 4) |
| `ai check` | plain-English report on anything wrong |
| `ai fix` | repairs what is safe to repair |
| `ai chat` | talk to an AI |
| `ai help` | one screen listing everything |
| `ai undo` | undoes the last change `ai` made |

**None of these can break the machine.** There is no delete in any of them.

## 6. In a web browser

From this machine, or from a laptop on the same network:

```
http://<this machine's address>:3000     the AI Cockpit
http://<this machine's address>:8443     the code editor
```

Type `ai help` to see the exact addresses. The editor's password is stored on
the machine; `ai help` tells you where.

---

# Credentials for this machine

**Fill these in by hand before handing the machine over.** They are deliberately
not stored in any file or repository — a password written into version control
stays recoverable in its history forever, long after anyone deletes it. A printed
sheet that travels with the hardware is the right place for them.

```
  Login username . . . . .  macpro

  Login password . . . . .  ______________________________

  Root password  . . . . .  ______________________________
                            (if one was set during install)
```

To set or change the login password, on the machine:

```bash
sudo passwd macpro
```

It asks twice and echoes nothing. That is the only place the password should be
typed.

### Everything else is not a password

| What | Where it lives on the machine |
|---|---|
| VS Code browser access | `cat ~/.vscode-web/connection-token` |
| AI provider keys | `/etc/ai-cockpit/env` — set them with `ai setup` |

Neither is a login credential, and both can be regenerated freely.

---

# What is installed on this machine

Everything below is already working. You do not have to install anything.

## The AI assistants

**All four AI assistants are in the editor too** — Copilot is built in, and
Claude, Gemini and ChatGPT/Codex are installed as extensions. Signing in to each
is covered in ACCOUNTS-AND-SIGN-IN.md.

| Command | What it is |
|---|---|
| `claude` | Claude Code. A coding and general assistant that runs in a Terminal window. |
| `claude-dark20` | The same thing with a dark colour scheme. |
| `claude-desktop` | Claude as a normal window with buttons, rather than in a Terminal. |
| `gemini` | Google's assistant, in a Terminal. Has a free option. |
| `codex` | OpenAI's coding assistant, in a Terminal. |
| `aider` | Edits files in a project for you, guided by conversation. |
| `gh` | GitHub from the command line. |

## Made for this machine

| Command | What it is |
|---|---|
| `ai` | **Start here.** Tells you what to do next, and fixes things. |
| `g5-copilot` | Ask "how do I …?" and it suggests a command. **It never runs it.** |
| `g5-codex` | Ask it to change a file. It shows you the change before applying it. |
| `g5-gemini` | A conversation, in plain text. |
| `ai-session` | A work session that survives closing the window. |
| `macpro-doctor` | Full health report on the hardware. |
| `macpro-telemetry` | The same information as data, refreshed every 5 minutes. |

The three `g5-` tools also work on the **old Mac OS X side** of this machine,
which nothing else does. They send their questions through the gateway below.

## The web apps

| Address | What it is |
|---|---|
| `:3000` | **The AI Cockpit.** Chat, a machine health page, and a tool that rewrites modern code so it runs on the 2006 Mac system. |
| `:8443` | **Visual Studio Code.** The real thing, in a browser. Works from your laptop too. Needs the access token — see below. |
| `:8081` | **The AI Gateway.** Not something you visit. It lets the old Mac OS X side reach modern AI services, which it cannot do on its own. |

Type `ai help` to see the exact addresses for this machine.

## Running quietly in the background

| | |
|---|---|
| **rasdaemon** | Watches the memory for errors. This is the early warning for the fault described overleaf. |
| **Automatic security updates** | Applied without you doing anything. |
| **Firewall** | Only your home network can reach this machine. Nothing is exposed to the internet. |
| **A local AI model** | Works with no internet at all, but is very slow (about a word per second). For emergencies. |

## Also installed — the everyday applications

All of these are in the **Applications** menu, top-left of the screen. You do
not need the AI to use any of them.

| | |
|---|---|
| **Firefox** | Web browser. Current version, not an old one. |
| **LibreOffice** | Documents, spreadsheets and presentations. Opens and saves Word and Excel files. |
| **VLC** | Plays video and music — essentially any file you give it. |
| **GIMP** | Photo and image editing. |
| **OpenShot** | Video editing on a timeline. |
| **Thunar** | The file manager, for browsing your files. |
| **Terminal** | Where you type the commands on this sheet. |

For programming, **Python** and **Node.js** are installed and current, along
with the tools to build software from source.

**The look of the desktop** — dark theme, icons, fonts — is in **Settings →
Appearance**. Change it freely; nothing depends on it.

**If you prefer something lighter**, a second desktop called **LXDE** is
installed. At the login screen, click the small icon near your name to pick it.
Xfce is the default and there is no need to change.

---

# If something goes wrong

## The screen is black and the fans are LOUD and never quieten

**This is a memory fault, and it has happened before.** Do not reinstall
anything.

Open the side panel and look for a small **red light labelled `T_FAULT`** on the
board at the front, below the fan.

If it is lit: switch off, unplug, and **push the memory sticks firmly back into
their slots** until the clips at both ends click up by themselves. They are on
two removable trays behind the front grille. This alone has fixed it.

The contacts are twenty years old. This will probably happen again one day, and
this is the fix.

## The screen goes black but the fans are NORMAL

Hold Option at power-on and choose the **second** menu line, "repair
filesystem". If that does not help, choose **Lion** instead — it almost always
starts — and the machine is still usable while you get help.

## Anything else

Log in, open a Terminal, and type:

```
ai check
```

It tests the network, the AI keys, every service and the disks, and prints a
numbered list of what to do about anything it finds.

---

# Two things to know about this machine

**It is from 2006, and the graphics are slow.** A browser and a terminal are
fine. Video is not. The screen is drawn entirely by the processor because this
graphics card has no modern driver. That is normal here, not a fault.

**One of the two hard disks is worn.** The disk holding the old Mac system has
failed to read data thousands of times over its life. It still works, but
**nothing on it is backed up.** Do not store anything on this machine that does
not exist somewhere else.

**The simplest backup is an external USB drive.** Plug one in, and copy your
work to it. No accounts, no subscription, no internet needed. A 1 TB drive costs
about the same as two months of coffee and is the right answer for this machine.

Cloud backup is optional and costs money -- see the full documentation if you
want it. You do not need it to use this machine safely.

---

# Full documentation

Everything is on the machine. Open a Terminal and type:

```
ls /usr/local/share/doc/macpro/kit/
```

Start with **NEW-OWNER-START-HERE.md**, then **ACCOUNTS-AND-SIGN-IN.md** (which
account each tool needs), then **FIRST-RUN-CHECKLIST.md**.

If the machine will not start at all, those same files are in the project
repository under `docs/g5-handoff/kit/`.

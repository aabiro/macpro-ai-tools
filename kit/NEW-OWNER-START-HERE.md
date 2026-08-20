# Start here

You do not need to know anything about Linux, git, editors or AI to use this
machine. This page is the whole of what you need on day one.

---

## The only thing you must remember

```
ai
```

Type that in a Terminal window and press Enter. It looks at the machine and tells
you what to do next. That is its entire job.

Everything else hangs off it:

| Type this | What it does |
|---|---|
| `ai` | tells you what to do next |
| `ai setup` | switches the AI on (do this first) |
| `ai check` | tells you, in plain English, if anything is wrong |
| `ai fix` | repairs the things that are safe to repair |
| `ai chat` | start talking to an AI |
| `ai help` | one screen listing everything |
| `ai undo` | puts back the last change `ai` made |

**None of those can break anything.** There is no delete anywhere in them.

## You do not have to type at all if you would rather not

On the desktop there are four icons:

- **Start Here** — a page explaining what to do, with clickable links
- **AI Cockpit** — chat with an AI, see the machine's health
- **Code Editor** — a full editor, in the browser
- **AI Terminal** — opens a window with `ai` already run

The **Start Here** page also opens by itself the first time you log in.

## Day one, in order

### 1. Switch the AI on

Open **AI Terminal** (or any Terminal) and type:

```
ai setup
```

It will:

1. show you the three providers and where to sign up (Gemini has a free tier)
2. ask you to paste the key
3. **test the key against the real service before saving anything**
4. save it, restart what needs restarting, and confirm it works

If the key is wrong, it tells you why in plain English and **saves nothing** —
the machine is left exactly as it was. You can run `ai setup` as many times as
you like.

This is the step that matters. Until it is done, nothing AI-related works, and
that is by design rather than a fault.

### 2. Check it worked

```
ai check
```

You want to see `OK` next to everything. If you see `PROBLEM`, it prints the
command that fixes it.

### 3. Try it

```
ai chat
```

Or open **AI Cockpit** from the desktop.

## When something goes wrong

It will, eventually. That is normal, and the machine is built to survive it.

```
ai check      what is wrong, in plain English
ai fix        repair it
```

`ai check` never guesses. It tests the network, the keys, each service, the
gateway and the disk, then prints a numbered list of what to do. `ai fix` only
restarts services and reloads configuration — it does not touch your files.

### If you changed a key and it broke

```
ai undo
```

Every time `ai setup` writes a key, the previous version is copied to
`/var/backups/ai-cockpit/` first. `ai undo` puts the most recent one back.

### If the screen goes black at startup

This machine has a specific, known graphics fault, and there is a boot menu
entry for it. Hold **Option** at power-on, pick the non-Apple icon, and choose:

```
Debian - repair filesystem (forced fsck)
```

The full explanation is in
[LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md). You do not need to
understand it, only to know that entry exists.

### If you are truly stuck

```
ai check > ~/Desktop/what-is-wrong.txt
```

That writes a file to your desktop describing the machine's state. Send it to
someone who can read it. It contains no passwords or keys.

## Things that cannot hurt you

The AI tools here are deliberately cautious:

- **`g5-copilot suggest "..."`** suggests a command and **never runs it**. If the
  suggestion is destructive, it says so before you copy it.
- **`g5-codex -m "..." file`** shows you the proposed change as a
  before-and-after first. It only writes with `--write`, and keeps a `.bak`.
- The AI's file access is limited to `~/projects`. It cannot reach the rest of
  the system even if asked.
- Security updates install themselves. You do not have to think about it.

## Things worth knowing eventually, not now

| | |
|---|---|
| Everything installed, and why | [AI-STACK.md](AI-STACK.md) |
| The full day-one checklist with proofs | [FIRST-RUN-CHECKLIST.md](FIRST-RUN-CHECKLIST.md) |
| Black screens and boot problems | [LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) |
| Making the machine faster or newer | [HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md) |

All of them are on the machine at `/usr/local/share/doc/macpro/kit/`.

## Two honest warnings

**This is a 2006 computer.** The desktop is usable but slow, because its
graphics card has no working driver and everything is drawn by the CPU. A
browser and a terminal are fine. Video is not. That is the hardware, not
something you have broken.

**One of the two hard disks has been quietly repairing itself for years** — 255
reallocated sectors on the drive holding the old Mac OS system. It passes its
own health check and may run for years more, but do not keep anything on this
machine that exists nowhere else. Set up backups (step 5 of the checklist).

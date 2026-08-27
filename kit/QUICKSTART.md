# Quick start

One page. Five steps. You do not need to understand the machine to use it.

If you want more detail later, everything else is in
[NEW-OWNER-START-HERE.md](NEW-OWNER-START-HERE.md).

---

## 1. Log in

Username **macpro**. The password came with the machine.

You land on a desktop with icons. That is the Linux side, and it is the side
you should use.

## 2. Do the one urgent thing first

There is an old Mac OS system on the second hard disk, and **that disk is
failing**. Nothing on it is backed up.

If the previous owner's photos, documents or music matter to anyone, copy them
off the machine **today**. Plug in a USB drive and open **Files** from the
desktop; the old system's files are under `/mnt/lion`.

If none of it matters, skip this. But decide now rather than later — the disk
has already patched around 255 damaged sectors.

## 3. Turn the AI on

Open **AI Terminal** from the desktop and type:

```
ai setup
```

It walks you through getting a key (Google Gemini has a free tier), tests the
key against the real service, and only saves it if it works. If the key is
wrong it tells you why and changes nothing.

Then check it:

```
ai check
```

You want `OK` next to everything. If something says `PROBLEM`, it prints the
command that fixes it.

## 4. Learn the two commands that matter

```
ai check      tells you in plain English if anything is wrong
ai fix        repairs what is safe to repair
```

Neither can delete anything. When something feels wrong, run `ai check` first.

## 5. Know what you have

Double-click **Start Here** on the desktop for clickable links, or read
[PROGRAMS-AND-APPS.md](PROGRAMS-AND-APPS.md) for the full list of what is
installed and what each thing is for.

---

## The desktop icons

| Icon | What it does |
|---|---|
| **Start Here** | A page of clickable links. Opens by itself on first login. |
| **AI Cockpit** | Chat with an AI and see the machine's health. |
| **AI Terminal** | A terminal with `ai` already run. |
| **Firefox** | Web browser. |
| **Files** | Browse your files. |
| **VS Code** | Write code. |
| **LibreOffice** | Documents, spreadsheets, presentations. |
| **GIMP** | Edit photos. |
| **OpenShot** | Edit video. |
| **VLC** | Play video and music. |
| **Terminal** | The plain command line. |

## Two things that are normal, not faults

**The desktop is slow.** This is a 2006 computer whose graphics card has no
working driver, so the processor draws everything. Browsing and writing are
fine. Playing video full-screen is not. Nothing is broken.

**About one start-up in three fails** — loud fans, no picture. Hold the power
button until it goes quiet, then start it again. It is a known hardware fault
and it cannot hurt your files.

## If the screen is black at start-up

Hold **Option** while powering on, pick the non-Apple icon, then choose:

```
Debian - repair filesystem (forced fsck)
```

You do not need to know why. Full explanation:
[LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md).

## If you are stuck

```
ai check > ~/Desktop/what-is-wrong.txt
```

That writes a file to your desktop describing the machine's state, with no
passwords or keys in it. Send it to someone who can read it.

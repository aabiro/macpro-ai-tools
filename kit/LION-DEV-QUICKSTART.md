# Editing Lion code from VS Code — quick start

You can open a project in VS Code on the Linux side whose files **are** Mac OS X
10.7.5 Lion's own files, edit them, and run them **inside Lion** — with an AI
assistant doing the edits and executing against Lion too. There is no copy step
and no per-session setup once this is done.

If you just want to use the machine, you do not need any of this — see
[QUICKSTART.md](QUICKSTART.md). This page is for writing and running Lion code.

---

## Once, to set it up

```bash
lion-vm start && lion-vm wait     # boot Lion as a VM (skip if already running)
lion-provision                    # install the cockpit inside Lion (one-off; persists)
lion-setup-editor                 # wire VS Code to the Lion project
```

`lion-setup-editor` is idempotent — run it again any time. It creates a
workspace, a **"Lion (root)"** terminal profile, a build task that runs the open
file in Lion, and `AGENTS.md`/`CLAUDE.md` telling an AI how to work here.

## Once, to sign the assistants in (no fallback)

```bash
lion-ai-login          # shows what is signed in and how to fix what is not
```

The loop uses **Claude Code** and **Codex** for real — never Gemini, and it
never silently skips. Sign each in once:

- **Claude Code** — `claude setup-token`, then **open the printed URL on your
  phone or laptop** (this machine's browser cannot finish the sign-in), approve,
  and paste the code back. This machine ships with no keys, by design.
- **Codex** — `codex exec` needs `OPENAI_API_KEY` in the environment:
  ```bash
  export OPENAI_API_KEY=sk-...      # this shell only; nothing is written to disk
  ```
  A ChatGPT login (`~/.codex/auth.json`) is **not** usable by `codex exec`.

Nothing above stores a key permanently — keeping this machine key-free is
deliberate.

## Every day

```bash
code ~/Lion-Demo.code-workspace
```

The **"Lion project (runs in Mac OS X)"** folder is Lion's own filesystem, at
`/mnt/lion-live/Users/Shared/lion-demo`. Edit `report.py`. Then:

- **Run it in Lion** — press the build key (**Ctrl+Shift+B**). Output appears in
  the terminal and in `.vscode/last-run.log`.
- **A shell inside Lion** — Terminal → new terminal → **"Lion (root)"**.
- **From any terminal** — `lion-run /mnt/lion-live/Users/Shared/lion-demo/report.py`,
  or a raw command with `lion 'sw_vers'`.

Path note: `/mnt/lion-live/Users/Shared/lion-demo` from Linux is
`/Users/Shared/lion-demo` inside Lion — strip the `/mnt/lion-live` prefix for
anything you hand to `lion`.

## Two realities of this hardware

- **VS Code must software-render.** There is no GPU driver, so
  `~/.vscode/argv.json` sets `disable-hardware-acceleration: true`. Leave it —
  without it VS Code fails with "GPU process isn't usable".
- **The browser cannot do OAuth here.** Sign-ins that open a browser loop
  forever. Do the sign-in step on your phone (above), or use the **browser
  editor** instead: it runs headless with no GPU at
  `http://<this-machine>:8443` (the token is in
  `~/.vscode-web/connection-token`). Open that from your laptop and open the
  same folder.

## To prove the whole loop works

```bash
cd ~/lion-e2e
OPENAI_API_KEY=sk-... DISPLAY=:0 XAUTHORITY=~/.Xauthority node vscode-lion.e2e.js
```

It drives the real VS Code, makes edits (including a real Codex edit), runs each
one inside Lion, and checks the result from outside the editor. Close any other
VS Code first — it refuses to run beside one, because two editors at once
overwhelm this framebuffer. Claude's stage stays red until you complete its
sign-in; everything else should pass.

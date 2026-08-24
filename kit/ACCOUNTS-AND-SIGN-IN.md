# Accounts you need, and how to sign in

Every AI tool on this machine needs an account with its provider. **None are
included** — no credentials of any previous owner are on this machine.

Work down the table. You do not need all of them; one is enough to start, and
Google Gemini has a free tier.

| Tool | Account needed | Free option? |
|---|---|---|
| Claude (CLI + editor) | Anthropic | no, pay per use |
| Gemini (CLI + editor) | Google | **yes** |
| ChatGPT / Codex (CLI + editor) | OpenAI | no, pay per use |
| GitHub Copilot (editor + `gh copilot`) | GitHub, with Copilot subscription | free for students/OSS maintainers |

---

## 1. The API keys — do this first

One command sets up everything that uses a key:

```bash
ai setup
```

It asks which provider, shows you the signup page, takes the pasted key,
**tests it against the real service, and only saves it if it works**. Nothing is
written if the key is wrong.

That single step configures:

- the `claude`, `gemini` and `codex` command-line tools
- the AI Cockpit web console
- the `g5-*` tools
- the gateway that lets the old Mac OS X side reach modern AI

Where to get each key:

| | |
|---|---|
| Anthropic | https://console.anthropic.com/settings/keys |
| Google Gemini | https://aistudio.google.com/apikey |
| OpenAI | https://platform.openai.com/api-keys |

## 2. Signing in to the editor extensions

The editor is **official Visual Studio Code**. Open it from the desktop, or in a
browser (see §4). Each AI extension signs in separately, from inside the editor.

### GitHub Copilot

Copilot Chat is **built into VS Code** — nothing to install. Click the Copilot
icon in the title bar and sign in with your GitHub account. It needs an active
Copilot subscription.

### Claude

The `anthropic.claude-code` extension is installed. Open the Claude panel and
sign in, or it will use the key you set with `ai setup`.

### Gemini Code Assist

The `google.geminicodeassist` extension is installed. Sign in with your Google
account when prompted.

### ChatGPT / Codex

The `openai.chatgpt` extension is installed. Sign in with your OpenAI account.

## 3. GitHub CLI and `gh copilot`

For git and Copilot in the terminal:

```bash
gh auth login                                # follow the prompts, browser-based
gh extension install github/gh-copilot       # only works after signing in
gh copilot suggest "find large files"
gh copilot explain "tar -xzvf archive.tar.gz"
```

`gh auth login` is also what lets you push to GitHub from this machine.

## 4. Reaching the editor from another computer

VS Code serves itself over the network on port **8443**, protected by a
connection token:

```bash
cat ~/.vscode-web/connection-token
```

Then from any browser on your network:

```
http://<this-machine-ip>:8443/?tkn=<that-token>
```

The firewall allows this from your local network and Tailscale only — never from
the internet. Do not port-forward it.

## 5. Optional: Tailscale

Only if you want to reach this machine from outside your home. It is installed
but **registered to nobody** — no previous owner's network is attached.

```bash
sudo tailscale up --hostname=macpro-g5
```

It prints a link; open it in a browser where you are signed in to **your own**
Tailscale account.

## What is NOT on this machine

- No API keys
- No signed-in accounts
- No Tailscale identity
- No cloud storage credentials

All deliberately blank. The machine was built and repaired remotely, then
stripped of every account before handover.

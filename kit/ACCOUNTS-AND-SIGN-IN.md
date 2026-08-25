# Accounts and keys — the complete beginner's guide

**Nothing on this machine can talk to an AI until you do this.** It takes about
ten minutes and you only have to do it once.

No accounts belonging to anyone else are on this machine. That is deliberate.

---

## First, what is an "API key"?

An API key is a long password that lets a program use an AI service on your
behalf. It looks like a jumble of letters and numbers:

```
AIzaSyB1c-EXAMPLE-not-a-real-key-9f2Kx
```

Three things to understand about it, and then you can stop thinking about it:

1. **It is not the same as your password.** You sign in to a website with your
   password; a program uses a key. If a key is ever exposed you delete it and
   make a new one, and nothing else about your account is affected.
2. **It is tied to money.** Using an AI costs the account that owns the key. See
   [What this costs](#what-this-costs) below before you start.
3. **It is a secret.** Never put a key in an email, a screenshot, a chat
   message, or a public web page.

## Which one should you get?

**Start with Google Gemini.** At the time of writing it has a free tier, which
means you can have this machine working today without entering a card. One
provider is enough — you do not need all of them.

| Provider | Powers | Free tier? |
|---|---|---|
| **Google Gemini** ← start here | `gemini`, the cockpit, the chat window, Mac OS X side | **yes** |
| Anthropic (Claude) | `claude`, Claude in the editor | no — pay per use |
| OpenAI (ChatGPT) | `codex`, ChatGPT in the editor | no — pay per use |
| GitHub | `gh`, GitHub Copilot in the editor | Copilot is paid, free for students and open-source maintainers |

---

# Part 1 — Get a Google Gemini key

Do this on **any** computer with a web browser. It does not have to be this one.

### Step 1 — sign in to Google

Go to **https://aistudio.google.com/apikey**

Sign in with a Google account. Any Gmail address works. If you do not have one,
the page will offer to make one.

> If you see a page asking you to accept terms, read it and accept it yourself.
> Nobody else can do that step for you.

### Step 2 — create the key

Click the button labelled **Create API key**.

A long string starting with `AIza` appears. **Click the copy icon next to it.**

That is the whole key. You will not be shown it again, so do not close the page
until the next part is finished.

### Step 3 — put it into this machine

On the Mac Pro, open **Terminal** (the icon on the desktop) and type:

```bash
ai setup
```

It will ask which provider — choose Google Gemini — and then ask for the key.
**Paste it** and press Enter.

> **Pasting into a terminal:** use **Ctrl+Shift+V**, or right-click and choose
> Paste. Plain Ctrl+V does not work in a terminal. You will not see the key
> appear as dots or stars — that is normal.

What happens next is automatic:

- it **tests the key against the real service** before saving anything
- if the key is wrong it says so and saves nothing, leaving the machine exactly
  as it was
- if the key works it saves it, switches the AI services on, and confirms

**You are done.** Try it:

```bash
ai chat
```

---

# Part 2 — the other providers (optional)

Only if you want them. The steps are the same shape: make a key on the
provider's site, then run `ai setup` again and choose that provider. You can
have several at once.

### Anthropic — for `claude`

1. Go to **https://console.anthropic.com/settings/keys**
2. Create an account, or sign in
3. **Add credit** — Anthropic has no free tier, so a key will not work until the
   account has money in it. Start with the smallest amount offered.
4. Click **Create Key**, copy it (it starts `sk-ant-`)
5. On this machine: `ai setup`

### OpenAI — for `codex` and ChatGPT

1. Go to **https://platform.openai.com/api-keys**
2. Create an account, or sign in
3. **Add credit** — same as Anthropic, there is no free tier for keys
4. Click **Create new secret key**, copy it (it starts `sk-`)
5. On this machine: `ai setup`

> A ChatGPT Plus subscription is **not** the same thing as API credit, and does
> not make an API key work. They are billed separately. This surprises people.

### GitHub — for `gh` and Copilot

This one uses a browser sign-in, not a pasted key. In Terminal:

```bash
gh auth login
```

Answer the prompts (choose **GitHub.com**, then **HTTPS**, then **login with a
web browser**). It shows an eight-character code and a URL. Open the URL,
type the code, approve it.

Then, for Copilot suggestions in the terminal:

```bash
gh extension install github/gh-copilot
gh copilot suggest "find the biggest files in my home folder"
```

Copilot needs a paid subscription, at **https://github.com/features/copilot**.
It is free if you are a student or maintain a popular open-source project.

---

# Part 3 — signing in inside the editor

The editor is **official Visual Studio Code** — the "VS Code" icon on the
desktop. Its AI extensions sign in *separately* from everything above, from
inside the editor itself.

| Extension | How to sign in |
|---|---|
| **GitHub Copilot** | Already built in. Click the Copilot icon in the title bar, sign in with GitHub. |
| **Claude** | Open the Claude panel in the sidebar and sign in, or it will use the key from `ai setup`. |
| **Gemini Code Assist** | Click the Gemini icon, sign in with your Google account. |
| **ChatGPT** | Click the ChatGPT icon, sign in with your OpenAI account. |

You do not need all four. Sign in to the one whose account you have.

---

# What this costs

This is the part people wish someone had told them.

**Gemini's free tier** has limits on how many messages per minute and per day.
Going over them makes it refuse politely until the next day. It does not charge
you. This is a good place to stay.

**Anthropic and OpenAI charge per use**, measured in "tokens" — roughly, pieces
of words, counting both your question and the answer. Ordinary conversational
use is cents, not dollars. Two habits keep it that way:

- **Set a spending limit** the day you create the account. Both providers offer
  one in their billing settings. Do it before you forget.
- **Long conversations cost more than short ones**, because the whole
  conversation is re-sent with each new message. Starting fresh is cheaper than
  continuing forever.

There is also a model that runs **on this machine**, costing nothing and needing
no key. It is not wired into the `ai` command, because at roughly a word per
second it is too slow to hold a conversation with. It exists for when the
internet is down, and you drive it directly:

```bash
/opt/llama.cpp/build/bin/llama-simple \
    -m /opt/models/qwen2.5-0.5b-instruct-q4_0.gguf \
    -n 40 "The capital of France is"
```

# Keeping your keys safe

| Do | Don't |
|---|---|
| Keep keys in `ai setup` only | Never paste a key into a chat, email, or screenshot |
| Delete and recreate a key you think was exposed | Don't reuse one key across machines you don't control |
| Set a spending limit | Don't leave a key in a file in your Documents folder |

If a key leaks, go to the provider's key page, delete it, create a new one, and
run `ai setup` again. That is the entire recovery procedure, and it is why keys
exist rather than using your password.

**Where your keys live on this machine:** one file,
`/etc/ai-cockpit/env`, readable only by the AI services and by `root`. Every
tool reads from that one place, so there is a single thing to change and a
single thing to protect.

# Checking it all works

```bash
ai check
```

That reports the network, whether a key is present, and whether each service is
running. If something is wrong it names the fix.

---

# Using this machine's AI from your phone or laptop

The gateway on this machine speaks the standard "OpenAI" language that most
chat apps understand. So a modern computer or phone on your home network can use
**this machine's keys** without ever having a copy of them.

Point any OpenAI-compatible app at:

```
http://<this-machine-ip>:8081/v1
```

Use any text you like as the app's "API key" — the real keys stay here. Find
this machine's address with:

```bash
hostname -I
```

Available model names are `gemini-flash-latest` (fast, the sensible default) and
`gemini-pro-latest` (slower, stronger), plus Claude and ChatGPT models if you
have added those keys.

> **Why this is the recommended way to get a polished chat window.** Modern chat
> interfaces such as Open WebUI will not run on this machine — its 2006 processor
> is missing instructions that today's numerical libraries require, and it fails
> immediately. Running the interface on a newer device and the *keys* here works
> perfectly. See AI-STACK.md for the full explanation.

This only works inside your own home network, by design. The firewall blocks it
from the internet. Do not open port 8081 on your router.

# Reaching the editor from another computer

VS Code also serves itself over your network on port **8443**, protected by a
token:

```bash
cat ~/.vscode-web/connection-token
```

Then in a browser on your network: `http://<this-machine-ip>:8443/?tkn=<token>`

# Optional: reaching this machine from outside your home

Only if you want that. Tailscale is installed but registered to nobody.

```bash
sudo tailscale up --hostname=macpro-g5
```

It prints a link. Open it in a browser where you are signed in to **your own**
Tailscale account. This is much safer than opening ports on your router — which
you should not do.

# What is NOT on this machine

- No API keys
- No signed-in accounts
- No Tailscale identity
- No cloud storage credentials

All deliberately blank, and verified empty at handover.

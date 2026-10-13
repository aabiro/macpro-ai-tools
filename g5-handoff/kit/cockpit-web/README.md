# Web Cockpit

A browser console for the Mac Pro 1,1 AI Cockpit. Runs on a **modern** machine
and combines everything: chat, machine diagnostics, code back-porting, and
gateway status.

## Why it runs here and not on the Mac Pro

It cannot run on the Mac Pro. No current version of Node.js supports Mac OS X
10.7, and Safari 6 cannot render a modern React app. So this runs on your
laptop or desktop and serves the vintage machine across the network — which is
the same shape as the gateway, just with a UI attached.

## It is a drop-in replacement for `aigw.py`

Both expose the identical contract:

```
GET  /health
POST /v1/chat/<provider>    { prompt, system?, history?, model?, max_tokens?, thinking? }
     ->                     { text, provider, model }
```

So the Mac Pro's terminal tools work against either one, unchanged. Verified on
the actual hardware — the same `g5-config test` passes against both:

```
Testing gateway at http://192.168.1.127:3000 ...     <- this app
  gateway version: 1.0.0-web
  model replied  : COCKPIT ONLINE

Testing gateway at http://192.168.1.127:8081 ...     <- aigw.py
  gateway version: 1.0.0
  model replied  : COCKPIT ONLINE
```

**Which should you run?**

| | |
|---|---|
| `aigw.py` | No install at all, Python 3 stdlib only. Always works. The reliable floor. |
| This app | Needs Node and `npm install`. Nicer to use, and gives you the tools in a browser. |

Run either. Or both, on different ports.

## Setup

```bash
npm install
export GEMINI_API_KEY=your-key-here      # or ANTHROPIC_API_KEY / OPENAI_API_KEY
npm run dev
```

Open <http://localhost:3000>.

The dev and start scripts bind `0.0.0.0` deliberately, so the Mac Pro can reach
this machine across the LAN. Point the Mac at it:

```bash
g5-config set gateway http://<this-machine-lan-ip>:3000
```

Use the LAN IP, not `localhost` — `localhost` on the Mac Pro means the Mac Pro.

For production use `npm run build && npm run start`.

## The four tools

**Oracle** — chat, with conversation history, against whichever provider has a key.

**Custodian** — paste the output of `g5-doctor --raw` from the Mac Pro and get
it interpreted by a model briefed as an Apple hardware technician. Useful
precisely when the Mac has *no* gateway configured, since `--raw` works fully
offline.

**Retro-Coder** — paste modern C/C++, Python, or shell and get it rewritten to
build on Lion. Note it targets **Intel/SSE**, not PowerPC/AltiVec — the original
project plan had the architecture wrong.

**Status** — gateway health, and the exact command to point the Mac at this app.

## Security

Your API key stays in this machine's environment. It is never sent to the Mac
Pro or to the browser — all provider calls happen server-side in the route
handler.

Unlike `aigw.py`, this app has **no client IP allowlist**. Next.js is intended
to sit behind whatever you deploy it with. On a home LAN that is fine. Do not
expose it to the public internet without putting authentication in front of it.

## Notes

- `thinkingBudget: 0` is set for Gemini by default. Current Gemini models are
  reasoning models that spend output tokens on thought before emitting text;
  at small budgets that returns truncated or empty answers. Measured on a
  one-line reply: 99 tokens with thinking, 11 without, same answer.
- Model defaults use `-latest` aliases rather than pinned versions, so the app
  keeps working when providers retire model IDs.

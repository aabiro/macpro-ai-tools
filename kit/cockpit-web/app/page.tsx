"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Tab = "chat" | "diagnose" | "retro" | "status";
type Provider = "gemini" | "anthropic" | "openai";
interface Message { role: "user" | "assistant"; content: string }
interface Health {
  status: string;
  version: string;
  providers_configured: Provider[];
  providers_supported: Provider[];
}

const CUSTODIAN_PROMPT = `You are a senior Apple hardware technician who has serviced Mac Pro towers since 2006. You are reading a diagnostic snapshot from a Mac Pro 1,1 (2006, dual Xeon 5150, FB-DIMM memory, mechanical drives) running Mac OS X 10.7 Lion.

Structure your answer exactly as:

VERDICT: one line - HEALTHY, WATCH, or ATTENTION NEEDED

FINDINGS: what you can actually see in the data, quoting the numbers.

WATCH LIST: age-related failure points for this model the data does not disprove - FB-DIMM failure, power supply ageing, dust and thermal paths, mechanical drives past service life.

DO THIS NEXT: concrete steps, most important first.

Do not invent readings that are not in the data.`;

const RETRO_PROMPTS: Record<string, string> = {
  c: `Rewrite the supplied C/C++ so it compiles cleanly on Mac OS X 10.7 Lion with Xcode 4.6.3 (Clang 4.2, C99/C++03 — NOT C++11).

Target hardware: Mac Pro 1,1, Intel Xeon 5150 (x86_64). Vector extensions: SSE, SSE2, SSE3, SSSE3. NOT SSE4.2, NOT AVX. This is an INTEL machine — do NOT emit AltiVec or any PowerPC intrinsics.

Replace C++11+ constructs with C++03 equivalents. Use BSD/Darwin calls, not Linux-only ones. Keep behaviour identical. Mark anything impossible with a comment starting // RETRO-PORT:

Output ONLY the rewritten code. No explanation, no markdown fences.`,
  python: `Rewrite the supplied Python so it runs on Python 2.7.1 (the interpreter on Mac OS X 10.7 Lion).

No f-strings (use %), print as a statement or __future__ import, urllib2 not urllib.request, os.path not pathlib, no type annotations, no dataclasses, no typing.

STANDARD LIBRARY ONLY — that machine cannot install packages, its TLS is too old to reach PyPI. Mark anything needing a third-party package with # RETRO-PORT:

Output ONLY the rewritten code. No explanation, no markdown fences.`,
  shell: `Rewrite the supplied shell script for bash 3.2 with the BSD userland on Mac OS X 10.7 Lion.

No associative arrays, no \${var^^}, no mapfile — those need bash 4. BSD tool flags, not GNU (sed -i needs an argument; stat/date/readlink differ). Assume no Homebrew, no GNU coreutils. Mark anything impossible with # RETRO-PORT:

Output ONLY the rewritten code. No explanation, no markdown fences.`,
};

async function ask(
  provider: Provider,
  body: Record<string, unknown>,
): Promise<string> {
  const res = await fetch(`/v1/chat/${provider}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.text || data.error || `HTTP ${res.status}`);
  return data.text as string;
}

export default function Cockpit() {
  const [tab, setTab] = useState<Tab>("chat");
  const [health, setHealth] = useState<Health | null>(null);
  const [provider, setProvider] = useState<Provider>("gemini");
  const [lanHint, setLanHint] = useState("");

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((h: Health) => {
        setHealth(h);
        if (h.providers_configured?.length && !h.providers_configured.includes(provider)) {
          setProvider(h.providers_configured[0]);
        }
      })
      .catch(() => setHealth(null));
    setLanHint(window.location.origin);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ready = health?.providers_configured ?? [];

  return (
    <main className="wrap">
      <header className="head">
        <div>
          <h1>AI COCKPIT</h1>
          {/* This console now runs on the Debian side of the machine and serves
              both OSes; the Retro-Coder prompts still target Lion, which is the
              whole point of them. */}
          <p className="sub">Mac Pro 1,1 &nbsp;//&nbsp; Debian 13 + OS X 10.7 Lion &nbsp;//&nbsp; web console</p>
        </div>
        <div className="hstat">
          {health ? (
            ready.length ? (
              <span className="pill ok">{ready.length} provider{ready.length > 1 ? "s" : ""} ready</span>
            ) : (
              <span className="pill bad">no API key set</span>
            )
          ) : (
            <span className="pill">connecting…</span>
          )}
          {ready.length > 1 && (
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              {ready.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          )}
        </div>
      </header>

      <nav className="tabs">
        {([
          ["chat", "Oracle"],
          ["diagnose", "Custodian"],
          ["retro", "Retro-Coder"],
          ["status", "Status"],
        ] as [Tab, string][]).map(([id, label]) => (
          <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </nav>

      {ready.length === 0 && health && <NoKeys />}

      <section className="panel">
        {tab === "chat" && <Chat provider={provider} disabled={!ready.length} />}
        {tab === "diagnose" && <Diagnose provider={provider} disabled={!ready.length} />}
        {tab === "retro" && <Retro provider={provider} disabled={!ready.length} />}
        {tab === "status" && <Status health={health} origin={lanHint} />}
      </section>
    </main>
  );
}

function NoKeys() {
  return (
    <div className="alert">
      <strong>No API key configured.</strong> Stop the server, set a key, and start it again:
      <pre>{`export GEMINI_API_KEY=your-key-here
npm run dev`}</pre>
      Get a free Gemini key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">aistudio.google.com/apikey</a>.
    </div>
  );
}

function Chat({ provider, disabled }: { provider: Provider; disabled: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    const history = messages.slice(-12);
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const reply = await ask(provider, { prompt: text, history, max_tokens: 2048 });
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠ ${(err as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  }, [input, busy, messages, provider]);

  return (
    <div className="chat">
      <div className="log">
        {messages.length === 0 && <p className="hint">Ask anything. Shift+Enter for a new line.</p>}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <span className="who">{m.role === "user" ? "YOU" : "AI"}</span>
            <div className="body">{m.content}</div>
          </div>
        ))}
        {busy && <div className="msg assistant"><span className="who">AI</span><div className="body blink">thinking…</div></div>}
        <div ref={endRef} />
      </div>
      <div className="composer">
        <textarea
          value={input}
          disabled={disabled}
          placeholder={disabled ? "Set an API key first" : "Message…"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); }
          }}
          rows={3}
        />
        <button onClick={() => void send()} disabled={disabled || busy || !input.trim()}>
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

function Diagnose({ provider, disabled }: { provider: Provider; disabled: boolean }) {
  const [raw, setRaw] = useState("");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!raw.trim() || busy) return;
    setBusy(true); setOut("");
    try {
      setOut(await ask(provider, { prompt: raw, system: CUSTODIAN_PROMPT, max_tokens: 1500 }));
    } catch (err) {
      setOut(`⚠ ${(err as Error).message}`);
    } finally { setBusy(false); }
  };

  return (
    <div className="tool">
      <p className="hint">
        On the Mac Pro run <code>g5-doctor --raw</code>, paste the output here, and get it
        interpreted. Useful when the Mac has no gateway configured — that command works
        entirely offline.
      </p>
      <textarea
        className="mono" rows={12} value={raw} disabled={disabled}
        placeholder="Paste the output of:  g5-doctor --raw"
        onChange={(e) => setRaw(e.target.value)}
      />
      <button onClick={() => void run()} disabled={disabled || busy || !raw.trim()}>
        {busy ? "Analysing…" : "Analyse"}
      </button>
      {out && <pre className="out">{out}</pre>}
    </div>
  );
}

function Retro({ provider, disabled }: { provider: Provider; disabled: boolean }) {
  const [lang, setLang] = useState("c");
  const [src, setSrc] = useState("");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (!src.trim() || busy) return;
    setBusy(true); setOut("");
    try {
      const budget = Math.max(2048, Math.min(8000, Math.floor(src.length / 2) + 1500));
      let text = await ask(provider, { prompt: src, system: RETRO_PROMPTS[lang], max_tokens: budget });
      text = text.replace(/^```[a-z]*\n?/i, "").replace(/```\s*$/, "");
      setOut(text);
    } catch (err) {
      setOut(`⚠ ${(err as Error).message}`);
    } finally { setBusy(false); }
  };

  return (
    <div className="tool">
      <p className="hint">
        Rewrite modern code so it builds on the Mac Pro: Clang 4.2 / C++03, Python 2.7,
        bash 3.2. Note it is an <strong>Intel</strong> machine (SSE), not a PowerPC G5 —
        the original project plan had this wrong.
      </p>
      <div className="row">
        <select value={lang} onChange={(e) => setLang(e.target.value)}>
          <option value="c">C / C++</option>
          <option value="python">Python</option>
          <option value="shell">Shell</option>
        </select>
        <button onClick={() => void run()} disabled={disabled || busy || !src.trim()}>
          {busy ? "Porting…" : "Port it"}
        </button>
      </div>
      <textarea
        className="mono" rows={12} value={src} disabled={disabled}
        placeholder="Paste modern source code here…"
        onChange={(e) => setSrc(e.target.value)}
      />
      {out && (
        <>
          <div className="row">
            <strong>Result</strong>
            <button onClick={() => void navigator.clipboard.writeText(out)}>Copy</button>
          </div>
          <pre className="out">{out}</pre>
          {out.includes("RETRO-PORT:") && (
            <div className="alert">
              Some parts could not be fully ported — search the result for
              <code> RETRO-PORT: </code> and review those by hand.
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Status({ health, origin }: { health: Health | null; origin: string }) {
  return (
    <div className="tool">
      <h2>Gateway status</h2>
      {health ? (
        <table className="kv">
          <tbody>
            <tr><td>Status</td><td>{health.status}</td></tr>
            <tr><td>Version</td><td>{health.version}</td></tr>
            <tr><td>Providers ready</td><td>{health.providers_configured.join(", ") || "none"}</td></tr>
            <tr><td>Providers supported</td><td>{health.providers_supported.join(", ")}</td></tr>
          </tbody>
        </table>
      ) : <p className="hint">Could not reach /health.</p>}

      <h2>Point the Mac Pro at this app</h2>
      <p className="hint">
        This app serves the <em>same</em> endpoints as the standalone Python gateway, so the
        Mac&apos;s terminal tools can use it directly. On the Mac Pro, in Terminal:
      </p>
      <pre className="out">{`g5-config set gateway ${origin || "http://<this-machine>:3000"}
g5-config test`}</pre>
      <p className="hint">
        Started with <code>next dev</code>? Use <code>-H 0.0.0.0</code> so the Mac can reach it
        across the network, and use this machine&apos;s LAN IP rather than{" "}
        <code>localhost</code>.
      </p>

      <h2>Which should I run?</h2>
      <table className="kv">
        <tbody>
          <tr><td><code>aigw.py</code></td><td>Zero install, always works, no UI. The reliable floor.</td></tr>
          <tr><td>This app</td><td>Needs Node and <code>npm install</code>. Nicer to use.</td></tr>
        </tbody>
      </table>
      <p className="hint">Either one. Both speak the identical contract.</p>
    </div>
  );
}

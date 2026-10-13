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

interface SmartDrive {
  health?: string; model?: string; power_on_hours?: number;
  reallocated_sectors?: number; pending_sectors?: number;
  offline_uncorrectable?: number; temperature_c?: number;
}
interface Telemetry {
  available: boolean;
  reason?: string;
  age_seconds?: number | null;
  hostname?: string;
  kernel?: string;
  load?: { load_1?: number; load_5?: number; load_15?: number; uptime_seconds?: number; cpu_count?: number };
  memory?: {
    total_mb?: number; used_percent?: number;
    zram?: { original_mb?: number; compressed_mb?: number; ratio?: number | null } | null;
  };
  ecc?: { correctable?: number; uncorrectable?: number; status?: string };
  smart?: Record<string, SmartDrive>;
  services?: Record<string, string>;
  display?: { framebuffer?: string; resolution?: string; radeon_loaded?: boolean };
  tailscale?: { state?: string; status?: string; self?: string };
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

  // Poll /health rather than fetching once on mount. Keys are added by editing
  // /etc/ai-cockpit/env and restarting the services, which happens outside this
  // app -- so every key-dependent piece of UI (the pill, the no-key banner, the
  // provider list, whether the inputs are enabled) has to be able to notice
  // that without the user reloading the page.
  useEffect(() => {
    let alive = true;
    const load = () =>
      fetch("/health", { cache: "no-store" })
        .then((r) => r.json())
        .then((h: Health) => {
          if (!alive) return;
          setHealth(h);
          // If the selected provider has no key but another does, move to it.
          const ok = h.providers_configured ?? [];
          if (ok.length && !ok.includes(provider)) setProvider(ok[0]);
        })
        .catch(() => alive && setHealth(null));
    load();
    const id = setInterval(load, 20000);
    return () => { alive = false; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider]);

  useEffect(() => { setLanHint(window.location.origin); }, []);

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
          {(health?.providers_supported?.length ?? 0) > 1 && (
            <select value={provider} onChange={(e) => setProvider(e.target.value as Provider)}>
              {health!.providers_supported.map((p) => (
                <option key={p} value={p} disabled={!ready.includes(p)}>
                  {p}{ready.includes(p) ? "" : " (no key)"}
                </option>
              ))}
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
      <strong>No API key configured.</strong> This console runs as a system service, so keys
      live in one file shared with the Python gateway. On the Mac Pro:
      <pre>{`sudo nano /etc/ai-cockpit/env
sudo systemctl restart ai-gateway cockpit-web`}</pre>
      Set any of <code>ANTHROPIC_API_KEY</code>, <code>GEMINI_API_KEY</code> or{" "}
      <code>OPENAI_API_KEY</code>. A free Gemini key is at{" "}
      <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">aistudio.google.com/apikey</a>.
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
        interpreted. Useful when the Mac has no gateway configured, since that command works
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
        bash 3.2.
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
              Some parts could not be fully ported. Search the result for
              <code> RETRO-PORT: </code> and review those by hand.
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Status({ health, origin }: { health: Health | null; origin: string }) {
  const [tel, setTel] = useState<Telemetry | null>(null);

  useEffect(() => {
    const load = () =>
      fetch("/telemetry").then((r) => r.json()).then(setTel).catch(() => setTel(null));
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, []);

  const supported = health?.providers_supported ?? [];
  const ready = health?.providers_configured ?? [];

  return (
    <div className="tool">
      <h2>Providers</h2>
      {health ? (
        <table className="kv">
          <tbody>
            {supported.map((p) => (
              <tr key={p}>
                <td>{p}</td>
                <td>
                  {ready.includes(p)
                    ? "key configured"
                    : "no key in /etc/ai-cockpit/env"}
                </td>
              </tr>
            ))}
            <tr><td>Gateway</td><td>{health.status} (v{health.version})</td></tr>
          </tbody>
        </table>
      ) : <p className="hint">Could not reach /health.</p>}

      <h2>Hardware</h2>
      {!tel ? (
        <p className="hint">Loading telemetry…</p>
      ) : !tel.available ? (
        <p className="hint">{tel.reason}</p>
      ) : (
        <>
          <table className="kv">
            <tbody>
              <tr><td>Host</td><td>{tel.hostname} / {tel.kernel}</td></tr>
              <tr><td>Uptime</td><td>{fmtUptime(tel.load?.uptime_seconds)}</td></tr>
              <tr><td>Load</td><td>{tel.load?.load_1} / {tel.load?.load_5} / {tel.load?.load_15} ({tel.load?.cpu_count} cores)</td></tr>
              <tr><td>Memory</td><td>{tel.memory?.used_percent}% of {gb(tel.memory?.total_mb)} used</td></tr>
              {tel.memory?.zram && (
                <tr><td>zram swap</td><td>
                  {tel.memory.zram.original_mb} MB stored in {tel.memory.zram.compressed_mb} MB
                  {tel.memory.zram.ratio ? ` (${tel.memory.zram.ratio}x)` : ""}
                </td></tr>
              )}
              <tr><td>ECC memory</td><td>{fmtEcc(tel.ecc)}</td></tr>
              <tr><td>Display</td><td>
                {tel.display?.framebuffer} @ {tel.display?.resolution}
                {tel.display?.radeon_loaded ? "" : " (radeon disabled by design)"}
              </td></tr>
              <tr><td>Tailscale</td><td>{tel.tailscale?.state ?? tel.tailscale?.status ?? "unknown"}{tel.tailscale?.self ? ` (${tel.tailscale.self})` : ""}</td></tr>
              <tr><td>Collected</td><td>{tel.age_seconds != null ? `${tel.age_seconds}s ago` : "unknown"}</td></tr>
            </tbody>
          </table>

          <h2>Drives</h2>
          <table className="kv">
            <tbody>
              {Object.entries(tel.smart ?? {}).map(([dev, d]) => {
                const bad = (d.reallocated_sectors ?? 0) > 0 || (d.pending_sectors ?? 0) > 0;
                return (
                  <tr key={dev}>
                    <td>{dev}{d.model ? ` (${d.model})` : ""}</td>
                    <td className={bad ? "warn" : undefined}>
                      {d.health ?? "unknown"}
                      {d.power_on_hours != null ? `, ${d.power_on_hours}h` : ""}
                      {d.reallocated_sectors != null ? `, ${d.reallocated_sectors} reallocated` : ""}
                      {d.pending_sectors != null ? `, ${d.pending_sectors} pending` : ""}
                      {d.temperature_c != null ? `, ${d.temperature_c}\u00b0C` : ""}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <h2>Services</h2>
          <table className="kv">
            <tbody>
              {Object.entries(tel.services ?? {}).map(([name, state]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td className={state === "active" ? undefined : "warn"}>{state}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h2>Point the Mac Pro at this app</h2>
      <p className="hint">
        This app serves the <em>same</em> endpoints as the standalone Python gateway, so the
        Mac&apos;s terminal tools can use it directly. On the Mac Pro, in Terminal:
      </p>
      <pre className="out">{`g5-config set gateway ${origin || "http://<this-machine>:3000"}
g5-config test`}</pre>

      <h2>Which should I run?</h2>
      <table className="kv">
        <tbody>
          <tr><td><code>aigw.py</code></td><td>Zero install, always works, no UI. The reliable floor.</td></tr>
          <tr><td>This app</td><td>Needs Node. Nicer to use. Runs as cockpit-web.service.</td></tr>
        </tbody>
      </table>
      <p className="hint">Both speak the identical contract, so either is fine.</p>
    </div>
  );
}

function gb(mb?: number) {
  return mb == null ? "?" : `${(mb / 1024).toFixed(1)} GB`;
}

function fmtUptime(s?: number) {
  if (s == null) return "unknown";
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`;
}

function fmtEcc(e?: Telemetry["ecc"]) {
  if (!e) return "unknown";
  if ("status" in e && e.status) return e.status;
  const ce = e.correctable ?? 0, ue = e.uncorrectable ?? 0;
  return ce === 0 && ue === 0
    ? "no errors"
    : `${ce} correctable, ${ue} uncorrectable`;
}

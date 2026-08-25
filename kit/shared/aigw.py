#!/usr/bin/env python3
"""
aigw.py -- The Vintage Mac AI Gateway.

A single-file, zero-dependency TLS bridge that lets a vintage Mac (Lion, Leopard,
Tiger -- anything whose OpenSSL is too old to speak TLS 1.2) talk to modern LLM APIs.

WHY THIS EXISTS
---------------
The Mac Pro ships with OpenSSL 0.9.8za and curl 7.21.4. Modern LLM endpoints
require TLS 1.2+. The vintage machine physically cannot complete the handshake:

    $ curl -o /dev/null -w '%{http_code}' https://api.anthropic.com
    000        <- not a 4xx or 5xx. No connection at all.

So the vintage Mac speaks plain HTTP to this gateway over your LAN, and this
gateway -- running on any machine made after ~2015 -- performs the modern TLS
handshake on its behalf and relays the answer back.

    [Mac Pro / Lion] --HTTP--> [aigw.py on modern box] --HTTPS/TLS1.3--> [LLM API]

DEPENDENCIES
------------
None. Python 3.7+ standard library only. No pip, no venv, no requirements.txt.
This is deliberate: the next owner should be able to run it on a fresh machine
in under a minute, on macOS, Linux, or Windows, without a toolchain.

QUICK START
-----------
    export ANTHROPIC_API_KEY=sk-ant-...      # and/or OPENAI_API_KEY, GEMINI_API_KEY
    python3 aigw.py

Then on the vintage Mac:

    curl -s http://<this-machine-lan-ip>:8081/health

SECURITY MODEL
--------------
  * API keys live ONLY on this modern machine, read from the environment.
    They are never written to disk and never sent to the vintage Mac.
  * The gateway binds to your LAN and refuses any client outside a private
    address range by default (RFC1918 + Tailscale CGNAT + loopback).
  * There is no auth beyond the network allowlist. Do NOT port-forward this to
    the public internet. It is a LAN appliance. If you need it off-LAN, put it
    behind a VPN (Tailscale/WireGuard) rather than exposing the port.
"""

import argparse
import ipaddress
import json
import os
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

__version__ = "1.1.0"

# --------------------------------------------------------------------------
# Provider definitions
# --------------------------------------------------------------------------
# Each provider knows three things: where to send the request, how to
# authenticate it, and how to dig the assistant's text out of the response.

PROVIDERS = {
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-sonnet-5",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o",
        "headers": lambda key: {
            "Authorization": "Bearer " + key,
            "content-type": "application/json",
        },
    },
    "gemini": {
        "env": "GEMINI_API_KEY",
        # Model is interpolated into the path at call time.
        "url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        # "-latest" alias rather than a pinned version: this machine is being
        # handed on, and a pinned model ID will start returning 404 the moment
        # the provider retires it. Aliases keep working with no code edits.
        "default_model": "gemini-flash-latest",
        "headers": lambda key: {
            "x-goog-api-key": key,
            "content-type": "application/json",
        },
    },
}


def api_key_for(provider):
    """Return the API key for a provider, or None if it is not configured."""
    spec = PROVIDERS.get(provider)
    if not spec:
        return None
    key = os.environ.get(spec["env"], "").strip()
    return key or None


def configured_providers():
    """Which providers actually have a key present right now."""
    return sorted(p for p in PROVIDERS if api_key_for(p))


# --------------------------------------------------------------------------
# OpenAI-compatible surface
# --------------------------------------------------------------------------
# Open WebUI -- and almost every other chat front-end -- speaks OpenAI's dialect
# and nothing else. Rather than teach each client about this gateway, the
# gateway grows a /v1/models and /v1/chat/completions that they already know.
# Keys stay in exactly one file, which was the point of the gateway.
#
# "thinking" is per-model and NOT cosmetic: the Gemini Pro models reject
# thinkingBudget: 0 outright with "This model only works in thinking mode", so
# sending the gateway's usual token-saving default at them fails every request.
# Flash models are happy with thinking off and answer faster, so they keep it.
OPENAI_MODELS = {
    # exposed id             provider     native model             thinking
    "gemini-pro-latest":    ("gemini",   "gemini-pro-latest",      True),
    "gemini-flash-latest":  ("gemini",   "gemini-flash-latest",    False),
    "gemini-3.1-pro":       ("gemini",   "gemini-3.1-pro-preview", True),
    "gemini-3.7-flash":     ("gemini",   "gemini-3.7-flash",       False),
    "claude-sonnet-5":      ("anthropic", "claude-sonnet-5",       False),
    "gpt-4o":               ("openai",   "gpt-4o",                 False),
}


def openai_catalog():
    """Only advertise models whose provider actually has a key."""
    ready = set(configured_providers())
    return [m for m, (prov, _, _) in sorted(OPENAI_MODELS.items()) if prov in ready]


def messages_to_gateway(messages):
    """Split an OpenAI messages[] array into (system, history, prompt).

    The gateway's native shape predates this endpoint and wants the final user
    turn separated from everything before it.
    """
    system_parts, history = [], []
    for msg in messages or []:
        role = msg.get("role")
        content = msg.get("content")
        # Newer clients may send content as a list of typed parts.
        if isinstance(content, list):
            content = "".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        content = (content or "").strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
        else:
            history.append({"role": role, "content": content})

    prompt = ""
    if history and history[-1]["role"] == "user":
        prompt = history.pop()["content"]
    return ("\n\n".join(system_parts) or None), history, prompt


# --------------------------------------------------------------------------
# Request shaping
# --------------------------------------------------------------------------
# The vintage clients speak one simple dialect; each provider speaks its own.
# These two functions translate between them so the Python 2.7 side stays dumb.


def build_payload(provider, prompt, system, history, model, max_tokens, thinking=False):
    """Translate a normalized request into the provider's native wire format.

    ``thinking`` defaults to False. Current Gemini models are reasoning models
    that spend output tokens on internal thought before emitting any text. On a
    vintage terminal that is doubly bad: the visible answer gets truncated (or
    comes back empty) at modest token budgets, and the user waits longer for it.
    Measured on gemini-flash-latest for a one-line reply:

        thinkingBudget 0 ->  11 total tokens, answer complete
        thinking on      ->  99 total tokens (88 of them thought), same answer

    So we switch thinking off unless a caller explicitly asks for it.
    """
    history = history or []

    if provider == "anthropic":
        messages = list(history) + [{"role": "user", "content": prompt}]
        payload = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system:
            payload["system"] = system
        return payload

    if provider == "openai":
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return {"model": model, "max_tokens": max_tokens, "messages": messages}

    if provider == "gemini":
        contents = []
        for msg in history:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        gen_config = {"maxOutputTokens": max_tokens}
        if not thinking:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}
        payload = {"contents": contents, "generationConfig": gen_config}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    raise ValueError("unknown provider: %s" % provider)


def extract_text(provider, result):
    """Pull the assistant's plain text out of a provider's response envelope."""
    try:
        if provider == "anthropic":
            blocks = result.get("content") or []
            parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            return "".join(parts).strip()

        if provider == "openai":
            return result["choices"][0]["message"]["content"].strip()

        if provider == "gemini":
            cand = result["candidates"][0]
            parts = cand.get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        pass

    # Never crash the vintage client over an unexpected shape -- hand back
    # something it can display so the user can see what actually came through.
    return "[gateway] Could not parse %s response: %s" % (
        provider,
        json.dumps(result)[:600],
    )


def call_provider(provider, payload, model, timeout=120):
    """Make the real HTTPS call. This is the only place TLS happens."""
    spec = PROVIDERS[provider]
    key = api_key_for(provider)
    if not key:
        raise RuntimeError(
            "%s is not configured -- set %s in this shell and restart the gateway"
            % (provider, spec["env"])
        )

    url = spec["url"].format(model=model)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=spec["headers"](key), method="POST")

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


# --------------------------------------------------------------------------
# HTTP surface
# --------------------------------------------------------------------------


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = "aigw/" + __version__
    protocol_version = "HTTP/1.1"

    # -- helpers ----------------------------------------------------------

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_sse(self, events):
        """Send a complete SSE body in one response.

        Deliberately buffered rather than incrementally streamed. The upstream
        providers are called with a single non-streaming request, so there is
        nothing to emit progressively anyway, and a buffered body keeps an
        accurate Content-Length -- which HTTP/1.1 needs and which chunked
        encoding on BaseHTTPRequestHandler makes needlessly fragile. Clients
        that expect a stream parse this identically; only the typewriter effect
        is lost.
        """
        body = "".join("data: %s\n\n" % e for e in events).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_openai_chat(self):
        """POST /v1/chat/completions -- OpenAI's dialect, spoken by Open WebUI."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            req = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"error": {"message": "bad JSON body: %s" % exc}})
            return

        model_id = (req.get("model") or "").strip()
        entry = OPENAI_MODELS.get(model_id)
        if not entry:
            self._send(404, {"error": {
                "message": "unknown model %r" % model_id,
                "available": openai_catalog(),
            }})
            return
        provider, native_model, thinking = entry

        if not api_key_for(provider):
            # 503 with a plain instruction: this is the state the machine ships
            # in, so the message has to say what to do rather than just fail.
            self._send(503, {"error": {"message":
                "No API key for %s. Add %s to /etc/ai-cockpit/env and run: "
                "sudo systemctl restart ai-gateway"
                % (provider, PROVIDERS[provider]["env"])}})
            return

        system, history, prompt = messages_to_gateway(req.get("messages"))
        if not prompt:
            self._send(400, {"error": {"message": "no user message in request"}})
            return

        try:
            # Generous default: with thinking on, the model spends part of this
            # budget reasoning before it writes anything, so a small cap can
            # return an empty answer that looks like a failure.
            max_tokens = int(req.get("max_tokens") or 8192)
        except (TypeError, ValueError):
            max_tokens = 8192

        try:
            payload = build_payload(provider, prompt, system, history,
                                    native_model, max_tokens, thinking)
            result = call_provider(provider, payload, native_model)
            text = extract_text(provider, result)
        except Exception as exc:                      # noqa: BLE001
            self._send(502, {"error": {"message": "%s: %s" % (type(exc).__name__, exc)}})
            return

        made = int(time.time())
        ident = "chatcmpl-aigw-%d" % made

        if req.get("stream"):
            self._send_sse([
                json.dumps({"id": ident, "object": "chat.completion.chunk",
                            "created": made, "model": model_id,
                            "choices": [{"index": 0,
                                         "delta": {"role": "assistant", "content": text},
                                         "finish_reason": None}]}),
                json.dumps({"id": ident, "object": "chat.completion.chunk",
                            "created": made, "model": model_id,
                            "choices": [{"index": 0, "delta": {},
                                         "finish_reason": "stop"}]}),
                "[DONE]",
            ])
            return

        self._send(200, {
            "id": ident, "object": "chat.completion", "created": made,
            "model": model_id,
            "choices": [{"index": 0,
                         "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    def _client_allowed(self):
        allow = self.server.allow_networks
        if allow is None:  # --allow-any
            return True
        try:
            addr = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        return any(addr in net for net in allow)

    def log_message(self, fmt, *args):
        if self.server.quiet:
            return
        sys.stderr.write("[aigw] %s %s\n" % (self.client_address[0], fmt % args))

    # -- routes -----------------------------------------------------------

    def do_GET(self):
        if not self._client_allowed():
            self._send(403, {"error": "client not in allowlist"})
            return

        if self.path in ("/health", "/"):
            self._send(
                200,
                {
                    "status": "ok",
                    "version": __version__,
                    "providers_configured": configured_providers(),
                    "providers_supported": sorted(PROVIDERS),
                },
            )
            return

        if self.path.rstrip("/") == "/v1/models":
            now = int(time.time())
            self._send(200, {
                "object": "list",
                "data": [
                    {"id": m, "object": "model", "created": now, "owned_by": "aigw"}
                    for m in openai_catalog()
                ],
            })
            return

        self._send(404, {"error": "no such route",
                         "try": ["/health", "/v1/models", "/v1/chat/completions"]})

    def do_POST(self):
        if not self._client_allowed():
            self._send(403, {"error": "client not in allowlist"})
            return

        # OpenAI dialect first: "/v1/chat/completions" also matches the legacy
        # "/v1/chat" prefix below, and would be misread as a provider name.
        if self.path.rstrip("/") == "/v1/chat/completions":
            self._handle_openai_chat()
            return

        # Accept /v1/chat, /v1/chat/<provider>, and the legacy
        # /v1/chat/<anything>/<provider> shape the first-generation client used.
        path = self.path.rstrip("/")
        provider_from_path = None
        if path.startswith("/v1/chat"):
            tail = [seg for seg in path[len("/v1/chat"):].split("/") if seg]
            for seg in reversed(tail):
                if seg in PROVIDERS:
                    provider_from_path = seg
                    break
        else:
            self._send(404, {"error": "no such route", "try": ["/v1/chat/<provider>"]})
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            req = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"error": "bad JSON body: %s" % exc})
            return

        provider = (req.get("provider") or provider_from_path or "").strip()
        if provider not in PROVIDERS:
            self._send(
                400,
                {
                    "error": "unknown or missing provider",
                    "supported": sorted(PROVIDERS),
                    "configured": configured_providers(),
                },
            )
            return

        prompt = req.get("prompt") or ""
        if not prompt.strip():
            self._send(400, {"error": "empty prompt"})
            return

        model = (req.get("model") or "").strip() or PROVIDERS[provider]["default_model"]
        system = req.get("system")
        history = req.get("history") or []
        try:
            max_tokens = int(req.get("max_tokens") or 2048)
        except (TypeError, ValueError):
            max_tokens = 2048
        thinking = bool(req.get("thinking"))

        try:
            payload = build_payload(
                provider, prompt, system, history, model, max_tokens, thinking
            )
            result = call_provider(provider, payload, model)
            text = extract_text(provider, result)
            self._send(200, {"text": text, "provider": provider, "model": model})

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            self._send(
                502,
                {
                    "error": "upstream %s returned HTTP %s" % (provider, exc.code),
                    "detail": detail,
                    "text": "[gateway] %s error %s: %s" % (provider, exc.code, detail),
                },
            )
        except (urllib.error.URLError, socket.timeout, ssl.SSLError) as exc:
            self._send(
                504,
                {
                    "error": "could not reach %s: %s" % (provider, exc),
                    "text": "[gateway] network error reaching %s: %s" % (provider, exc),
                },
            )
        except RuntimeError as exc:
            self._send(503, {"error": str(exc), "text": "[gateway] " + str(exc)})
        except Exception as exc:  # noqa: BLE001 - never take the gateway down
            self._send(
                500,
                {"error": "gateway fault: %s" % exc, "text": "[gateway] fault: %s" % exc},
            )


# --------------------------------------------------------------------------
# Startup
# --------------------------------------------------------------------------

DEFAULT_ALLOW = [
    "127.0.0.0/8",     # loopback
    "10.0.0.0/8",      # RFC1918
    "172.16.0.0/12",   # RFC1918
    "192.168.0.0/16",  # RFC1918 -- the Mac Pro lives here
    "100.64.0.0/10",   # CGNAT / Tailscale
    "::1/128",
    "fd00::/8",
]


def lan_ip():
    """Best-effort LAN IP, so we can print a copy-pasteable URL for the Mac."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))  # no packets sent; just picks the route
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Zero-dependency TLS bridge for vintage Macs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: all interfaces)")
    parser.add_argument("--port", type=int, default=8081, help="bind port (default: 8081)")
    parser.add_argument(
        "--allow",
        action="append",
        default=None,
        metavar="CIDR",
        help="allowed client network; repeatable. Defaults to private ranges only.",
    )
    parser.add_argument(
        "--allow-any",
        action="store_true",
        help="DANGEROUS: accept any client IP. Only for debugging on a trusted network.",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress per-request logging")
    parser.add_argument("--version", action="version", version="aigw " + __version__)
    args = parser.parse_args(argv)

    if args.allow_any:
        allow_networks = None
    else:
        allow_networks = [
            ipaddress.ip_network(cidr, strict=False) for cidr in (args.allow or DEFAULT_ALLOW)
        ]

    ready = configured_providers()

    print("=" * 68)
    print(" Vintage Mac AI Gateway  v%s" % __version__)
    print("=" * 68)
    if ready:
        print(" Providers ready : %s" % ", ".join(ready))
    else:
        print(" Providers ready : NONE")
        print()
        print(" No API keys found in this shell. Set at least one and restart:")
        for name, spec in sorted(PROVIDERS.items()):
            print("     export %-20s # enables %s" % (spec["env"] + "=...", name))
        print()
        print(" The gateway will still start, but every request will return 503.")

    missing = [p for p in sorted(PROVIDERS) if p not in ready]
    if ready and missing:
        print(" Not configured  : %s" % ", ".join(missing))

    print(" Listening on    : http://%s:%s" % (args.host, args.port))
    print(" Reach it at     : http://%s:%s" % (lan_ip(), args.port))
    print(" Client access   : %s" % ("ANY (unrestricted!)" if allow_networks is None
                                     else "private networks only"))
    print()
    print(" On the Mac Pro, point the cockpit at this gateway:")
    print("     g5-config set gateway http://%s:%s" % (lan_ip(), args.port))
    print()
    print(" Ctrl-C to stop.")
    print("=" * 68)

    httpd = ThreadingHTTPServer((args.host, args.port), GatewayHandler)
    httpd.allow_networks = allow_networks
    httpd.quiet = args.quiet
    httpd.daemon_threads = True

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[aigw] shutting down.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

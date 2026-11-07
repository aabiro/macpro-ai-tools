/**
 * Provider definitions — the TypeScript twin of the PROVIDERS table in
 * kit/gateway/aigw.py.
 *
 * Both implementations expose the SAME contract:
 *
 *     GET  /health
 *     POST /v1/chat/<provider>   { prompt, system?, history?, model?,
 *                                  max_tokens?, thinking? }
 *              ->                { text, provider, model }
 *
 * That is deliberate. The Mac Pro's Python 2.7 clients can point at either one,
 * so the new owner can run the zero-dependency Python gateway OR this web app
 * and nothing on the vintage side needs to change.
 */

export type ProviderName = "anthropic" | "openai" | "gemini";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  prompt: string;
  system?: string;
  history?: ChatMessage[];
  model?: string;
  max_tokens?: number;
  thinking?: boolean;
}

interface ProviderSpec {
  envKey: string;
  url: (model: string) => string;
  defaultModel: string;
  headers: (key: string) => Record<string, string>;
  buildPayload: (req: Required<Pick<ChatRequest, "prompt">> & ChatRequest, model: string) => unknown;
  extractText: (result: any) => string | null;
}

export const PROVIDERS: Record<ProviderName, ProviderSpec> = {
  anthropic: {
    envKey: "ANTHROPIC_API_KEY",
    url: () => "https://api.anthropic.com/v1/messages",
    defaultModel: "claude-sonnet-5",
    headers: (key) => ({
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    }),
    buildPayload: (req, model) => {
      const messages = [...(req.history ?? []), { role: "user", content: req.prompt }];
      const payload: Record<string, unknown> = {
        model,
        max_tokens: req.max_tokens ?? 2048,
        messages,
      };
      if (req.system) payload.system = req.system;
      return payload;
    },
    extractText: (result) =>
      Array.isArray(result?.content)
        ? result.content
            .filter((b: any) => b?.type === "text")
            .map((b: any) => b.text ?? "")
            .join("")
            .trim() || null
        : null,
  },

  openai: {
    envKey: "OPENAI_API_KEY",
    url: () => "https://api.openai.com/v1/chat/completions",
    defaultModel: "gpt-4o",
    headers: (key) => ({
      Authorization: `Bearer ${key}`,
      "content-type": "application/json",
    }),
    buildPayload: (req, model) => {
      const messages: ChatMessage[] | { role: string; content: string }[] = [];
      if (req.system) messages.push({ role: "system", content: req.system } as any);
      messages.push(...((req.history ?? []) as any));
      messages.push({ role: "user", content: req.prompt } as any);
      return { model, max_tokens: req.max_tokens ?? 2048, messages };
    },
    extractText: (result) => result?.choices?.[0]?.message?.content?.trim() ?? null,
  },

  gemini: {
    envKey: "GEMINI_API_KEY",
    url: (model) =>
      `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
    // A "-latest" alias rather than a pinned version. This kit is handed on;
    // a pinned model ID starts returning 404 the moment it is retired.
    defaultModel: "gemini-flash-latest",
    headers: (key) => ({
      "x-goog-api-key": key,
      "content-type": "application/json",
    }),
    buildPayload: (req, model) => {
      void model;
      const contents = (req.history ?? []).map((m) => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }],
      }));
      contents.push({ role: "user", parts: [{ text: req.prompt }] });

      const generationConfig: Record<string, unknown> = {
        maxOutputTokens: req.max_tokens ?? 2048,
      };
      // Current Gemini models spend output tokens on internal reasoning before
      // emitting text. Measured for a one-line reply: thinking on = 99 tokens
      // (88 of them thought); thinking off = 11 tokens, same answer. Small
      // budgets come back truncated or empty with it on, so default it off.
      if (!req.thinking) {
        generationConfig.thinkingConfig = { thinkingBudget: 0 };
      }

      const payload: Record<string, unknown> = { contents, generationConfig };
      if (req.system) payload.systemInstruction = { parts: [{ text: req.system }] };
      return payload;
    },
    extractText: (result) => {
      const parts = result?.candidates?.[0]?.content?.parts;
      if (!Array.isArray(parts)) return null;
      return parts.map((p: any) => p?.text ?? "").join("").trim() || null;
    },
  },
};

/**
 * The model name is the one caller-supplied part of an upstream URL. Only allow
 * the characters real model IDs use, so a key can only ever be sent to a model
 * path on its own provider's host.
 */
const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/;

export function apiKeyFor(provider: ProviderName): string | null {
  const key = process.env[PROVIDERS[provider].envKey]?.trim();
  return key ? key : null;
}

export function configuredProviders(): ProviderName[] {
  return (Object.keys(PROVIDERS) as ProviderName[]).filter((p) => apiKeyFor(p)).sort();
}

export class ProviderError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = "ProviderError";
  }
}

/** Perform the real HTTPS call. This is the only place TLS happens. */
export async function callProvider(
  provider: ProviderName,
  req: ChatRequest,
): Promise<{ text: string; provider: ProviderName; model: string }> {
  const spec = PROVIDERS[provider];
  const key = apiKeyFor(provider);
  if (!key) {
    throw new ProviderError(
      `${provider} is not configured — set ${spec.envKey} and restart`,
      503,
    );
  }

  const model = req.model?.trim() || spec.defaultModel;
  if (!MODEL_ID.test(model)) {
    throw new ProviderError(`invalid model name: ${JSON.stringify(model)}`, 400);
  }
  const payload = spec.buildPayload({ ...req, prompt: req.prompt }, model);

  let response: Response;
  try {
    response = await fetch(spec.url(model), {
      method: "POST",
      headers: spec.headers(key),
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (err) {
    throw new ProviderError(
      `could not reach ${provider}: ${(err as Error).message}`,
      504,
    );
  }

  const raw = await response.text();
  if (!response.ok) {
    throw new ProviderError(
      `upstream ${provider} returned HTTP ${response.status}`,
      502,
      raw.slice(0, 800),
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new ProviderError(`${provider} sent a non-JSON reply`, 502, raw.slice(0, 400));
  }

  const text = spec.extractText(parsed);
  if (!text) {
    throw new ProviderError(
      `could not parse the ${provider} reply`,
      502,
      JSON.stringify(parsed).slice(0, 600),
    );
  }

  return { text, provider, model };
}

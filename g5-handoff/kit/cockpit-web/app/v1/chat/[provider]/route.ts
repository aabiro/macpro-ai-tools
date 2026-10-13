import { NextRequest, NextResponse } from "next/server";
import {
  PROVIDERS,
  ProviderError,
  ProviderName,
  callProvider,
  configuredProviders,
} from "@/lib/providers";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

/**
 * POST /v1/chat/<provider>
 *
 * The same contract aigw.py serves, so the Mac Pro's Python 2.7 clients can be
 * pointed at this app instead of the standalone gateway with no changes.
 *
 * Errors always include a `text` field as well as `error`, because the vintage
 * clients display `text` directly — a failure should show the user a sentence,
 * not a stack trace.
 */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> },
) {
  const { provider: rawProvider } = await context.params;

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "bad JSON body" }, { status: 400 });
  }

  const provider = ((body.provider as string) || rawProvider || "").trim() as ProviderName;
  if (!(provider in PROVIDERS)) {
    return NextResponse.json(
      {
        error: "unknown or missing provider",
        supported: Object.keys(PROVIDERS).sort(),
        configured: configuredProviders(),
      },
      { status: 400 },
    );
  }

  const prompt = ((body.prompt as string) ?? "").trim();
  if (!prompt) {
    return NextResponse.json({ error: "empty prompt" }, { status: 400 });
  }

  try {
    const result = await callProvider(provider, {
      prompt,
      system: body.system as string | undefined,
      history: (body.history as any) ?? [],
      model: body.model as string | undefined,
      max_tokens: Number(body.max_tokens) || 2048,
      thinking: Boolean(body.thinking),
    });
    return NextResponse.json(result);
  } catch (err) {
    if (err instanceof ProviderError) {
      const message = err.detail ? `${err.message}: ${err.detail}` : err.message;
      return NextResponse.json(
        { error: err.message, detail: err.detail, text: `[gateway] ${message}` },
        { status: err.status },
      );
    }
    const message = (err as Error).message;
    return NextResponse.json(
      { error: `gateway fault: ${message}`, text: `[gateway] fault: ${message}` },
      { status: 500 },
    );
  }
}

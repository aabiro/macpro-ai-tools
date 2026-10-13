import { NextResponse } from "next/server";
import { PROVIDERS, configuredProviders } from "@/lib/providers";

export const dynamic = "force-dynamic";

/**
 * GET /health
 *
 * Byte-compatible with aigw.py's /health so the Mac Pro's `g5-config test`
 * cannot tell the two apart.
 */
export function GET() {
  return NextResponse.json({
    status: "ok",
    version: "1.0.0-web",
    providers_configured: configuredProviders(),
    providers_supported: Object.keys(PROVIDERS).sort(),
  });
}

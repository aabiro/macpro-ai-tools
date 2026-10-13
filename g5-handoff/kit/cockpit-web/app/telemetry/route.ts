import { readFile } from "node:fs/promises";
import { NextResponse } from "next/server";

/**
 * Hardware health for the Status tab.
 *
 * The file is written every 5 minutes by macpro-telemetry.timer, atomically via
 * rename, so a reader never sees a partial file. We only read it here: the web
 * app runs as an unprivileged service account and must not be collecting SMART
 * or ECC data itself.
 *
 * A missing file is a normal state (timer not installed, or first 45 seconds
 * after boot), so it returns 200 with available:false rather than an error. The
 * Status tab can then say something useful instead of rendering an exception.
 */

const TELEMETRY_PATH =
  process.env.TELEMETRY_PATH ?? "/var/lib/macpro-telemetry/latest.json";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const raw = await readFile(TELEMETRY_PATH, "utf8");
    const data = JSON.parse(raw);
    const ageSeconds =
      typeof data.collected_at === "number"
        ? Math.max(0, Math.floor(Date.now() / 1000) - data.collected_at)
        : null;
    return NextResponse.json(
      { available: true, age_seconds: ageSeconds, ...data },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (err) {
    const code = (err as NodeJS.ErrnoException)?.code;
    return NextResponse.json(
      {
        available: false,
        reason:
          code === "ENOENT"
            ? "No telemetry yet. Is macpro-telemetry.timer enabled?"
            : `Could not read telemetry: ${(err as Error).message}`,
        path: TELEMETRY_PATH,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  }
}

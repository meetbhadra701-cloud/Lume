/**
 * Next.js server-side proxy for /rate
 *
 * Browser calls /api/rate → this route handler → FastAPI /rate
 * TYPO_API_BASE_URL is server-side only
 */
import { NextRequest, NextResponse } from "next/server";

const TYPO_API_BASE_URL =
  process.env.TYPO_API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);

  try {
    const body = await request.json();

    const response = await fetch(`${TYPO_API_BASE_URL}/rate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (err: unknown) {
    clearTimeout(timeout);

    if (err instanceof Error && err.name === "AbortError") {
      return NextResponse.json(
        { error: { code: "timeout", message: "Backend request timed out (5s)" } },
        { status: 504 }
      );
    }

    const message =
      err instanceof Error ? err.message : "Failed to reach backend";
    return NextResponse.json(
      { error: { code: "network_error", message } },
      { status: 502 }
    );
  }
}

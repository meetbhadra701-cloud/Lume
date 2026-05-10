import { NextRequest, NextResponse } from "next/server";

const TYPO_BASE = process.env.TYPO_API_BASE_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);

  try {
    const body = await req.json();
    const res = await fetch(`${TYPO_BASE}/generate-mcq`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    clearTimeout(timeout);
    if (err instanceof Error && err.name === "AbortError") {
      return NextResponse.json(
        { error: { code: "timeout", message: "Request timed out" } },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { error: { code: "network_error", message: "Could not reach backend" } },
      { status: 502 }
    );
  }
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const DEMO_API_KEY = process.env.NEXT_PUBLIC_DEMO_API_KEY?.trim();

export function withDemoApiKey(headers?: HeadersInit): Headers {
  const result = new Headers(headers);
  if (DEMO_API_KEY) {
    result.set("X-Demo-Api-Key", DEMO_API_KEY);
  }
  return result;
}

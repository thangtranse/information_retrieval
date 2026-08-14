import { env } from "@/shared/config/env";

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(status: number, message?: string) {
    super(message ?? `API request failed with status ${status}`);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  // WHY: One transport boundary keeps status validation consistent across features.
  const response = await fetch(`${env.apiBaseUrl}${path}`, init);

  if (!response.ok) {
    let message: string | undefined;
    try {
      const payload = (await response.json()) as { detail?: string | { reason?: string } };
      message = typeof payload.detail === "string" ? payload.detail : payload.detail?.reason;
    } catch {
      // WHY: Error bodies are optional; status remains a stable fallback when parsing fails.
    }
    throw new ApiRequestError(response.status, message);
  }

  return response.json() as Promise<T>;
}

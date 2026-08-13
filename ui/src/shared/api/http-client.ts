import { env } from "@/shared/config/env";

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  // WHY: One transport boundary keeps status validation consistent across features.
  const response = await fetch(`${env.apiBaseUrl}${path}`, init);

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

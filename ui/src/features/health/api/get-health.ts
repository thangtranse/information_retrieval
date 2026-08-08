import { requestJson } from "../../../shared/api/http-client";
import type { Health } from "../model/health";

export function getHealth(): Promise<Health> {
  // WHY: A feature-owned gateway prevents transport details from leaking into UI components.
  return requestJson<Health>("/api/v1/health");
}

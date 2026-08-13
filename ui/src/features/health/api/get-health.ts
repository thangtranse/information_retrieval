import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

import type { Health } from "@/features/health/model/health";

export function getHealth(): Promise<Health> {
  // WHY: A feature-owned gateway prevents transport details from leaking into UI components.
  return requestJson<Health>(API_ENDPOINTS.health);
}

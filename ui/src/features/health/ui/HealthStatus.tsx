import { useEffect, useState } from "react";

import { getHealth } from "../api/get-health";
import type { Health } from "../model/health";

type HealthState =
  | { kind: "loading" }
  | { kind: "ready"; health: Health }
  | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    // WHY: Cancellation avoids committing a stale network result after the component unmounts.
    let active = true;

    void getHealth()
      .then((health) => {
        if (active) setState({ kind: "ready", health });
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : "Unknown API error";
          setState({ kind: "error", message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") return <p>Checking backend…</p>;
  if (state.kind === "error") return <p role="alert">Backend unavailable: {state.message}</p>;

  return (
    <dl className="health-card">
      <div><dt>Status</dt><dd>{state.health.status}</dd></div>
      <div><dt>Service</dt><dd>{state.health.service}</dd></div>
      <div><dt>Environment</dt><dd>{state.health.environment}</dd></div>
    </dl>
  );
}

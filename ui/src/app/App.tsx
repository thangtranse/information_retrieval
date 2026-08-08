import { HealthStatus } from "../features/health/ui/HealthStatus";

export function App() {
  return (
    <main className="app-shell">
      <header>
        <p className="eyebrow">System foundation</p>
        <h1>Information Retrieval</h1>
        <p>Python backend and web UI are connected through a typed HTTP boundary.</p>
      </header>
      <section aria-labelledby="backend-status">
        <h2 id="backend-status">Backend status</h2>
        <HealthStatus />
      </section>
    </main>
  );
}

export default function SettingsPage() {
  return (
    <section className="stack">
      <h2>Settings</h2>
      <div className="card stack">
        <h3>Current MVP configuration</h3>
        <p><strong>Database:</strong> SQLite through Prisma.</p>
        <p><strong>Generation:</strong> deterministic fallback only. AI provider abstraction can be added in Phase 2.</p>
        <p><strong>Submission:</strong> manual only. No auto-submit exists.</p>
        <p><strong>Refresh:</strong> placeholder script exists at <code>scripts/refresh-jobs.ts</code>.</p>
      </div>
      <div className="card stack">
        <h3>Phase 2 source files</h3>
        <p>Use <code>data/job_sources.sample.json</code> for ATS source configuration.</p>
        <p>Use <code>data/sponsor_companies.sample.csv</code> for licensed sponsor evidence.</p>
        <p>Use <code>data/base_profile.md</code> as the profile source for tailored generation.</p>
      </div>
    </section>
  );
}

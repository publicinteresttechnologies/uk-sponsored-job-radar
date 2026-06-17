import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function DashboardPage() {
  const [total, ready, rejected, applied, review] = await Promise.all([
    prisma.job.count(),
    prisma.job.count({ where: { status: 'READY_TO_APPLY' } }),
    prisma.job.count({ where: { status: 'REJECTED' } }),
    prisma.job.count({ where: { status: 'APPLIED' } }),
    prisma.job.count({ where: { status: 'REVIEW' } })
  ]);

  return (
    <div className="grid">
      <section className="card">
        <h2>Total jobs</h2>
        <p style={{ fontSize: 36, margin: 0 }}>{total}</p>
      </section>
      <section className="card">
        <h2>Ready to apply</h2>
        <p style={{ fontSize: 36, margin: 0 }}>{ready}</p>
      </section>
      <section className="card">
        <h2>Review</h2>
        <p style={{ fontSize: 36, margin: 0 }}>{review}</p>
      </section>
      <section className="card">
        <h2>Rejected</h2>
        <p style={{ fontSize: 36, margin: 0 }}>{rejected}</p>
      </section>
      <section className="card">
        <h2>Applied</h2>
        <p style={{ fontSize: 36, margin: 0 }}>{applied}</p>
      </section>
      <section className="card">
        <h2>Operating rule</h2>
        <p>No blind auto-apply. This cockpit prepares evidence-led applications and keeps final submission manual.</p>
      </section>
    </div>
  );
}

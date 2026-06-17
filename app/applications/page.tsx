import { JobList } from '@/components/job-list';
import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function ApplicationsPage() {
  const jobs = await prisma.job.findMany({
    where: { status: 'APPLIED' },
    include: { rejectionReasons: true, applicationPack: true },
    orderBy: [{ updatedAt: 'desc' }]
  });

  return (
    <section className="stack">
      <h2>Applications tracker</h2>
      <p className="muted">Roles marked as applied. Final submission stays outside this app.</p>
      <JobList jobs={jobs} />
    </section>
  );
}

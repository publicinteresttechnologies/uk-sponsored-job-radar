import { JobList } from '@/components/job-list';
import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function RejectedJobsPage() {
  const jobs = await prisma.job.findMany({
    where: { status: 'REJECTED' },
    include: { rejectionReasons: true, applicationPack: true },
    orderBy: [{ createdAt: 'desc' }]
  });

  return (
    <section className="stack">
      <h2>Rejected jobs</h2>
      <p className="muted">Rejected roles remain visible so the filter can be audited and improved.</p>
      <JobList jobs={jobs} />
    </section>
  );
}

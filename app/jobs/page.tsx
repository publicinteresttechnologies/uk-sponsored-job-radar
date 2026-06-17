import { JobList } from '@/components/job-list';
import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function JobsPage() {
  const jobs = await prisma.job.findMany({
    include: { rejectionReasons: true, applicationPack: true },
    orderBy: [{ status: 'asc' }, { overallScore: 'desc' }, { createdAt: 'desc' }]
  });

  return (
    <section className="stack">
      <h2>All jobs</h2>
      <JobList jobs={jobs} />
    </section>
  );
}

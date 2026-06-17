import { JobList } from '@/components/job-list';
import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function ReadyJobsPage() {
  const jobs = await prisma.job.findMany({
    where: { status: 'READY_TO_APPLY' },
    include: { rejectionReasons: true, applicationPack: true },
    orderBy: [{ overallScore: 'desc' }, { createdAt: 'desc' }]
  });

  return (
    <section className="stack">
      <h2>Ready to apply</h2>
      <p className="muted">Only roles that pass the first sponsorship, salary/SOC and CV-fit gates.</p>
      <JobList jobs={jobs} />
    </section>
  );
}

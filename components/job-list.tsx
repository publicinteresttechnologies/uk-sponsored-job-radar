import Link from 'next/link';
import type { ApplicationPack, Job, RejectionReason } from '@prisma/client';
import { generatePack, markApplied, rejectJob } from '@/app/actions';

type JobWithRelations = Job & {
  rejectionReasons: RejectionReason[];
  applicationPack?: ApplicationPack | null;
};

function statusClass(status: string) {
  if (status === 'READY_TO_APPLY') return 'badge ready';
  if (status === 'REJECTED') return 'badge rejected';
  return 'badge review';
}

export function JobList({ jobs }: { jobs: JobWithRelations[] }) {
  if (jobs.length === 0) {
    return <div className="card">No jobs in this view yet. Run the seed command first.</div>;
  }

  return (
    <div className="stack">
      {jobs.map((job) => (
        <article className="card stack" key={job.id}>
          <div>
            <div className="row">
              <span className={statusClass(job.status)}>{job.status.replaceAll('_', ' ')}</span>
              <span className="badge">Fit {job.cvFitScore}</span>
              <span className="badge">Visa {job.salarySocScore}</span>
              <span className="badge">Overall {job.overallScore}</span>
            </div>
            <h2 style={{ marginTop: 12 }}>{job.title}</h2>
            <p className="muted">{job.companyName} · {job.location ?? 'Location unknown'} · {job.atsType ?? 'ATS unknown'}</p>
          </div>

          <div className="row">
            <Link className="button" href={`/jobs/${job.id}`}>View JD</Link>
            {job.officialApplicationUrl ? (
              <a className="button" href={job.officialApplicationUrl} target="_blank" rel="noreferrer">Open Official Application</a>
            ) : null}
            <form action={generatePack.bind(null, job.id)}>
              <button type="submit">Generate Pack</button>
            </form>
            <form action={markApplied.bind(null, job.id)}>
              <button type="submit">Mark Applied</button>
            </form>
            <form action={rejectJob.bind(null, job.id)}>
              <button type="submit">Reject</button>
            </form>
          </div>

          {job.rejectionReasons.length > 0 ? (
            <div>
              <strong>Rejection reasons</strong>
              <ul>
                {job.rejectionReasons.map((reason) => (
                  <li key={reason.id}><code>{reason.code}</code>: {reason.message}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

import { notFound } from 'next/navigation';
import { generatePack, markApplied, rejectJob } from '@/app/actions';
import { prisma } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function JobDetailPage({ params }: { params: { id: string } }) {
  const job = await prisma.job.findUnique({
    where: { id: params.id },
    include: { rejectionReasons: true, applicationPack: true }
  });

  if (!job) notFound();

  return (
    <section className="stack">
      <div className="card stack">
        <div className="row">
          <span className="badge">{job.status.replaceAll('_', ' ')}</span>
          <span className="badge">Fit {job.cvFitScore}</span>
          <span className="badge">Visa {job.salarySocScore}</span>
          <span className="badge">Overall {job.overallScore}</span>
        </div>
        <h2>{job.title}</h2>
        <p className="muted">{job.companyName} · {job.location ?? 'Location unknown'} · {job.atsType ?? 'ATS unknown'}</p>
        <p><strong>Role family:</strong> {job.detectedRoleFamily ?? 'unknown'}</p>
        <p><strong>Seniority:</strong> {job.detectedSeniority ?? 'unknown'}</p>
        <p><strong>Sponsor status:</strong> {job.sponsorStatus}</p>
        {job.sponsorshipEvidence ? <p><strong>Sponsor evidence:</strong> {job.sponsorshipEvidence}</p> : null}
        {job.salaryText ? <p><strong>Salary:</strong> {job.salaryText}</p> : null}
        <div className="row">
          {job.officialApplicationUrl ? (
            <a className="button" href={job.officialApplicationUrl} target="_blank" rel="noreferrer">Open Official Application</a>
          ) : null}
          <form action={generatePack.bind(null, job.id)}><button type="submit">Generate Pack</button></form>
          <form action={markApplied.bind(null, job.id)}><button type="submit">Mark Applied</button></form>
          <form action={rejectJob.bind(null, job.id)}><button type="submit">Reject</button></form>
        </div>
      </div>

      {job.rejectionReasons.length > 0 ? (
        <div className="card">
          <h3>Rejection reasons</h3>
          <ul>
            {job.rejectionReasons.map((reason) => (
              <li key={reason.id}><code>{reason.code}</code>: {reason.message}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="card">
        <h3>Job description</h3>
        <div className="textbox">{job.jdText}</div>
      </div>

      {job.applicationPack ? (
        <div className="grid">
          <section className="card"><h3>Tailored CV bullets</h3><pre>{job.applicationPack.tailoredCvBullets}</pre></section>
          <section className="card"><h3>Cover letter</h3><pre>{job.applicationPack.coverLetter}</pre></section>
          <section className="card"><h3>Recruiter note</h3><pre>{job.applicationPack.recruiterNote}</pre></section>
          <section className="card"><h3>Why me</h3><pre>{job.applicationPack.whyMeSummary}</pre></section>
          <section className="card"><h3>Sponsorship positioning</h3><pre>{job.applicationPack.sponsorshipPositioning}</pre></section>
          <section className="card"><h3>ATS screening suggestions</h3><pre>{job.applicationPack.atsScreeningSuggestions}</pre></section>
          <section className="card"><h3>Risk notes</h3><pre>{job.applicationPack.riskNotes}</pre></section>
        </div>
      ) : (
        <div className="card">No application pack yet. Use Generate Pack.</div>
      )}
    </section>
  );
}

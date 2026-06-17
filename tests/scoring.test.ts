import { describe, expect, it } from 'vitest';
import { getRejectionReasons, scoreCvFit, scoreJob, scoreSalarySocViability } from '../lib/scoring';

const baseJob = {
  companyName: 'Example Streaming UK',
  title: 'Senior Creative Producer',
  location: 'London',
  sourceUrl: 'https://example.com/job',
  officialApplicationUrl: 'https://example.com/job',
  jdText: 'Senior creative producer role across branded content, entertainment, video, partnerships and content strategy. Skilled Worker visa sponsorship available.',
  salaryText: '£50,000',
  sponsorStatus: 'EXPLICIT' as const,
  sponsorshipEvidence: 'JD says sponsorship available.'
};

describe('scoring', () => {
  it('scores a strong creative producer role as ready', () => {
    const scored = scoreJob(baseJob);
    expect(scored.status).toBe('READY_TO_APPLY');
    expect(scored.cvFitScore).toBeGreaterThanOrEqual(45);
    expect(scored.salarySocScore).toBeGreaterThanOrEqual(45);
  });

  it('rejects jobs without sponsor evidence', () => {
    const reasons = getRejectionReasons({ ...baseJob, sponsorStatus: 'NONE', sponsorshipEvidence: '', jdText: 'Senior creative producer role.' });
    expect(reasons.some((reason) => reason.code === 'NO_SPONSOR_EVIDENCE')).toBe(true);
  });

  it('penalises low salary or unpaid roles', () => {
    const score = scoreSalarySocViability({ ...baseJob, salaryText: 'Unpaid volunteer role', jdText: 'Unpaid volunteer content assistant.' });
    expect(score).toBeLessThan(45);
  });

  it('penalises low-fit engineering roles', () => {
    const score = scoreCvFit({ ...baseJob, title: 'Frontend Engineer', jdText: 'Software engineer role requiring backend APIs and production engineering.' });
    expect(score).toBeLessThan(45);
  });
});

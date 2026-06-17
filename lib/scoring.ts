import type { SponsorStatus } from '@prisma/client';

export type ScoringInput = {
  title: string;
  companyName: string;
  location?: string | null;
  sourceUrl: string;
  officialApplicationUrl?: string | null;
  jdText: string;
  salaryText?: string | null;
  sponsorStatus?: SponsorStatus | 'UNKNOWN' | 'LICENSED' | 'EXPLICIT' | 'NONE';
  sponsorshipEvidence?: string | null;
};

export type ScoredJob = {
  detectedSeniority: string;
  detectedRoleFamily: string;
  salarySocScore: number;
  cvFitScore: number;
  overallScore: number;
  status: 'REJECTED' | 'REVIEW' | 'READY_TO_APPLY';
  rejectionReasons: Array<{ code: string; message: string }>;
};

const positiveKeywords = [
  'producer',
  'development',
  'content',
  'creative',
  'partnerships',
  'media',
  'communications',
  'strategy',
  'branded content',
  'entertainment',
  'factual',
  'unscripted',
  'video',
  'tv',
  'television',
  'comedy',
  'gtm',
  'customer success',
  'partnerships manager',
  'content strategy',
  'creator',
  'campaign',
  'editorial'
];

const strongKeywords = [
  'development producer',
  'creative producer',
  'content producer',
  'senior producer',
  'branded content',
  'factual entertainment',
  'unscripted',
  'television',
  'media partnerships',
  'content strategy'
];

const negativeKeywords = [
  'intern',
  'internship',
  'volunteer',
  'unpaid',
  'junior assistant',
  'admin assistant',
  'receptionist',
  'warehouse',
  'retail assistant',
  'barista',
  'software engineer',
  'backend engineer',
  'frontend engineer',
  'full stack engineer'
];

function normalise(value?: string | null) {
  return (value ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function combined(job: ScoringInput) {
  return normalise(`${job.title} ${job.companyName} ${job.location ?? ''} ${job.jdText} ${job.salaryText ?? ''}`);
}

function containsAny(text: string, terms: string[]) {
  return terms.some((term) => text.includes(term));
}

export function detectSeniority(job: ScoringInput) {
  const text = combined(job);
  if (/\b(chief|vp|vice president|svp|director|head of)\b/.test(text)) return 'senior_leadership';
  if (/\b(senior|lead|principal|manager)\b/.test(text)) return 'senior_or_manager';
  if (/\b(associate|executive|coordinator)\b/.test(text)) return 'mid_or_entry';
  if (/\b(intern|assistant|junior)\b/.test(text)) return 'junior';
  return 'unknown';
}

export function detectRoleFamily(job: ScoringInput) {
  const text = combined(job);
  if (/\b(unscripted|television|tv|factual|entertainment|producer|development producer)\b/.test(text)) {
    return 'tv_content_production';
  }
  if (/\b(branded content|creative strategy|campaign|creative producer|content strategy)\b/.test(text)) {
    return 'branded_content_strategy';
  }
  if (/\b(partnership|business development|gtm|customer success|account manager)\b/.test(text)) {
    return 'partnerships_gtm';
  }
  if (/\b(communications|pr|media relations|editorial)\b/.test(text)) return 'media_comms';
  if (/\b(engineer|developer|software|data scientist)\b/.test(text)) return 'technical_low_fit';
  return 'unknown';
}

export function scoreCvFit(job: ScoringInput) {
  const text = combined(job);
  let score = 0;

  for (const keyword of positiveKeywords) {
    if (text.includes(keyword)) score += 5;
  }
  for (const keyword of strongKeywords) {
    if (text.includes(keyword)) score += 10;
  }
  if (detectSeniority(job) === 'senior_or_manager') score += 12;
  if (detectSeniority(job) === 'senior_leadership') score += 8;
  if (detectRoleFamily(job) === 'technical_low_fit') score -= 40;
  if (containsAny(text, negativeKeywords)) score -= 35;

  return Math.max(0, Math.min(100, score));
}

export function scoreSalarySocViability(job: ScoringInput) {
  const text = combined(job);
  const salary = normalise(job.salaryText);
  let score = 20;

  const salaryNumbers = [...salary.matchAll(/£?\s?(\d{2,3})(?:,?000|k)/g)].map((m) => Number(m[1]) * 1000);
  const maxSalary = salaryNumbers.length ? Math.max(...salaryNumbers) : null;

  if (maxSalary && maxSalary >= 45000) score += 55;
  else if (maxSalary && maxSalary >= 41700) score += 45;
  else if (maxSalary && maxSalary >= 35000) score += 10;
  else if (maxSalary && maxSalary < 35000) score -= 35;

  if (/\b(senior|lead|manager|director|head of|principal)\b/.test(text)) score += 20;
  if (/\b(part time|temporary|zero hours|internship|apprentice|volunteer|unpaid)\b/.test(text)) score -= 45;
  if (/\b(fixed term|ftc|contract)\b/.test(text) && !/sponsor|visa|skilled worker/.test(text)) score -= 25;

  return Math.max(0, Math.min(100, score));
}

export function hasSponsorEvidence(job: ScoringInput) {
  const text = combined(job);
  return (
    job.sponsorStatus === 'LICENSED' ||
    job.sponsorStatus === 'EXPLICIT' ||
    Boolean(job.sponsorshipEvidence?.trim()) ||
    /\b(sponsorship|visa sponsorship|skilled worker|certificate of sponsorship|cos)\b/.test(text)
  );
}

export function getRejectionReasons(job: ScoringInput) {
  const text = combined(job);
  const reasons: Array<{ code: string; message: string }> = [];

  if (!job.officialApplicationUrl && !job.sourceUrl) {
    reasons.push({ code: 'NO_OFFICIAL_URL', message: 'No official company or ATS application URL is available.' });
  }
  if (!hasSponsorEvidence(job)) {
    reasons.push({ code: 'NO_SPONSOR_EVIDENCE', message: 'No licensed-sponsor or explicit sponsorship evidence is attached.' });
  }
  if (scoreSalarySocViability(job) < 45) {
    reasons.push({ code: 'SALARY_SOC_RISK', message: 'Salary or seniority appears weak for Skilled Worker viability.' });
  }
  if (scoreCvFit(job) < 45) {
    reasons.push({ code: 'LOW_CV_FIT', message: 'The role does not strongly match Karan’s TV/content/partnerships profile.' });
  }
  if (containsAny(text, negativeKeywords)) {
    reasons.push({ code: 'NEGATIVE_ROLE_SIGNAL', message: 'The role contains junior, unpaid, assistant, retail, warehouse, or pure engineering signals.' });
  }
  if (/\b(fixed term|ftc|contract)\b/.test(text) && !/sponsor|visa|skilled worker/.test(text)) {
    reasons.push({ code: 'FTC_WITHOUT_SPONSORSHIP', message: 'FTC/contract role without explicit sponsorship evidence.' });
  }

  return reasons;
}

export function scoreJob(job: ScoringInput): ScoredJob {
  const cvFitScore = scoreCvFit(job);
  const salarySocScore = scoreSalarySocViability(job);
  const detectedSeniority = detectSeniority(job);
  const detectedRoleFamily = detectRoleFamily(job);
  const rejectionReasons = getRejectionReasons(job);
  const sponsorBoost = hasSponsorEvidence(job) ? 15 : 0;
  const overallScore = Math.max(0, Math.min(100, Math.round(cvFitScore * 0.5 + salarySocScore * 0.35 + sponsorBoost)));
  const status = rejectionReasons.length > 0 ? 'REJECTED' : overallScore >= 65 ? 'READY_TO_APPLY' : 'REVIEW';

  return {
    detectedSeniority,
    detectedRoleFamily,
    salarySocScore,
    cvFitScore,
    overallScore,
    status,
    rejectionReasons
  };
}

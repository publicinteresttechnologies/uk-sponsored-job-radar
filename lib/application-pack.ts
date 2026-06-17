import type { Job } from '@prisma/client';

const profileSummary = `Karan Dhar is an Indian unscripted TV and entertainment producer with 7+ years across major mass-audience formats including Indian Idol, Bigg Boss, The Voice India, Dance India Dance, and India's Got Talent. He has an NFTS MA in Television Entertainment and is an RTS Student Television Award winner.`;

export function generateApplicationPack(job: Job) {
  const role = `${job.title} at ${job.companyName}`;
  const family = job.detectedRoleFamily ?? 'content/media';

  const tailoredCvBullets = [
    `Position Karan as a high-volume unscripted TV/content producer for ${role}, emphasising experience on national entertainment formats.`,
    `Lead with NFTS MA Television Entertainment and RTS Student Television Award as UK credibility signals.`,
    `Map Indian mass-audience production experience to ${family} needs: editorial judgement, stakeholder management, fast turnarounds, talent-facing work, and audience instincts.`,
    `Include sponsorship context only as a practical availability point, not as the main pitch.`
  ].join('\n');

  const coverLetter = `Dear Hiring Team,\n\nI am applying for ${role}. My background is in unscripted television, entertainment formats, branded/content development, and audience-led storytelling. I have worked across major Indian formats including Indian Idol, Bigg Boss, The Voice India, Dance India Dance, and India's Got Talent, and I later completed the MA Television Entertainment at the National Film and Television School in the UK.\n\nWhat I would bring to ${job.companyName} is a combination of mass-audience editorial instinct, production discipline, format awareness, and the ability to turn ambiguous creative or commercial briefs into usable output. I am especially interested in this role because it appears to sit close to my strongest lane: content, development, creative production, partnerships, or media strategy.\n\nI am currently in the UK and would require Skilled Worker sponsorship. I am raising that clearly because I only want to proceed where the role and employer can realistically support that route.\n\nBest,\nKaran Dhar`;

  const recruiterNote = `Hi — I am interested in ${role}. I am a UK-based NFTS MA Television Entertainment graduate and RTS Student Television Award winner with 7+ years across major Indian unscripted entertainment formats including Indian Idol, Bigg Boss, The Voice India, Dance India Dance, and India's Got Talent. The role looks close to my content/creative/partnerships background. I would require Skilled Worker sponsorship, so I wanted to check whether this role can support that before applying in full.`;

  const whyMeSummary = [
    '7+ years on major unscripted entertainment formats.',
    'NFTS MA Television Entertainment gives UK market credibility.',
    'RTS Student Television Award winner.',
    'Strong fit for content, development, creative production, partnerships, and media strategy roles.',
    'Can translate mass-audience entertainment experience into practical UK content/commercial output.'
  ].join('\n');

  const sponsorshipPositioning = `Karan is already in the UK on the Graduate route and is seeking a Skilled Worker sponsorship pathway. The application should be positioned around role fit first, with sponsorship handled clearly and practically. Do not imply sponsorship is guaranteed unless the employer or job advert explicitly says so.`;

  const atsScreeningSuggestions = [
    'Do you require sponsorship? Answer truthfully: Yes, Skilled Worker sponsorship would be required.',
    'Why this role? Emphasise content/creative production fit, audience judgement, format experience, and UK NFTS training.',
    'Salary expectations: keep aligned with Skilled Worker viability and role seniority; do not undercut below viable threshold.',
    'Right to work: state current UK Graduate route status and sponsorship requirement clearly.'
  ].join('\n');

  const riskNotes = [
    job.sponsorshipEvidence ? `Sponsor evidence: ${job.sponsorshipEvidence}` : 'No explicit sponsorship evidence stored. Verify before applying.',
    job.salaryText ? `Salary text: ${job.salaryText}` : 'Salary not stored. Verify salary/SOC viability before applying.',
    `Detected family: ${job.detectedRoleFamily ?? 'unknown'}.`,
    `Detected seniority: ${job.detectedSeniority ?? 'unknown'}.`
  ].join('\n');

  return {
    tailoredCvBullets,
    coverLetter,
    recruiterNote,
    whyMeSummary,
    sponsorshipPositioning,
    atsScreeningSuggestions,
    riskNotes,
    profileSummary
  };
}

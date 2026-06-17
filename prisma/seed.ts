import { PrismaClient, SponsorStatus } from '@prisma/client';
import { scoreJob } from '../lib/scoring';

const prisma = new PrismaClient();

type SeedJob = {
  companyName: string;
  title: string;
  location: string;
  sourceUrl: string;
  officialApplicationUrl: string;
  atsType: string;
  jdText: string;
  salaryText?: string;
  sponsorStatus: SponsorStatus;
  sponsorshipEvidence?: string;
};

const jobs: SeedJob[] = [
  {
    companyName: 'Example Media Studios',
    title: 'Senior Creative Producer, Branded Entertainment',
    location: 'London',
    sourceUrl: 'https://careers.example.com/senior-creative-producer',
    officialApplicationUrl: 'https://careers.example.com/senior-creative-producer',
    atsType: 'greenhouse',
    jdText: 'Senior creative producer role across branded content, video, entertainment, partnerships, editorial development and campaign production. Skilled Worker visa sponsorship can be considered for the right candidate.',
    salaryText: '£48,000 - £58,000',
    sponsorStatus: SponsorStatus.EXPLICIT,
    sponsorshipEvidence: 'JD states Skilled Worker visa sponsorship can be considered.'
  },
  {
    companyName: 'Example Streaming UK',
    title: 'Content Partnerships Manager',
    location: 'London',
    sourceUrl: 'https://jobs.example-streaming.com/content-partnerships-manager',
    officialApplicationUrl: 'https://jobs.example-streaming.com/content-partnerships-manager',
    atsType: 'lever',
    jdText: 'Partnerships manager for UK entertainment, creator, video and content strategy. Requires stakeholder management, editorial judgement, commercial instincts and media experience.',
    salaryText: 'Competitive senior manager package',
    sponsorStatus: SponsorStatus.LICENSED,
    sponsorshipEvidence: 'Company appears in configured licensed sponsor sample list.'
  },
  {
    companyName: 'Tiny Theatre Charity',
    title: 'Volunteer Content Assistant',
    location: 'Remote',
    sourceUrl: 'https://tinytheatre.example/jobs/volunteer-content-assistant',
    officialApplicationUrl: 'https://tinytheatre.example/jobs/volunteer-content-assistant',
    atsType: 'manual',
    jdText: 'Unpaid volunteer content assistant internship helping with admin, social posts and reception work.',
    salaryText: 'Unpaid',
    sponsorStatus: SponsorStatus.NONE
  },
  {
    companyName: 'Example SaaS',
    title: 'Frontend Engineer',
    location: 'London',
    sourceUrl: 'https://example-saas.example/jobs/frontend-engineer',
    officialApplicationUrl: 'https://example-saas.example/jobs/frontend-engineer',
    atsType: 'ashby',
    jdText: 'Software engineer role requiring React, TypeScript, backend APIs, distributed systems and production engineering ownership.',
    salaryText: '£70,000',
    sponsorStatus: SponsorStatus.LICENSED,
    sponsorshipEvidence: 'Company appears in configured licensed sponsor sample list.'
  },
  {
    companyName: 'Example Indie Production',
    title: 'Development Producer FTC',
    location: 'Manchester',
    sourceUrl: 'https://indie.example/jobs/development-producer-ftc',
    officialApplicationUrl: 'https://indie.example/jobs/development-producer-ftc',
    atsType: 'manual',
    jdText: 'Six month fixed term contract for a development producer in factual entertainment and unscripted TV. No visa sponsorship available.',
    salaryText: '£38,000 pro rata',
    sponsorStatus: SponsorStatus.NONE
  }
];

async function main() {
  for (const job of jobs) {
    const scored = scoreJob(job);
    const company = await prisma.company.upsert({
      where: { name: job.companyName },
      update: {
        sponsorStatus: job.sponsorStatus,
        sponsorshipEvidence: job.sponsorshipEvidence
      },
      create: {
        name: job.companyName,
        sponsorStatus: job.sponsorStatus,
        sponsorshipEvidence: job.sponsorshipEvidence
      }
    });

    const saved = await prisma.job.upsert({
      where: {
        companyName_title_sourceUrl: {
          companyName: job.companyName,
          title: job.title,
          sourceUrl: job.sourceUrl
        }
      },
      update: {
        ...job,
        companyId: company.id,
        detectedSeniority: scored.detectedSeniority,
        detectedRoleFamily: scored.detectedRoleFamily,
        salarySocScore: scored.salarySocScore,
        cvFitScore: scored.cvFitScore,
        overallScore: scored.overallScore,
        status: scored.status
      },
      create: {
        ...job,
        companyId: company.id,
        detectedSeniority: scored.detectedSeniority,
        detectedRoleFamily: scored.detectedRoleFamily,
        salarySocScore: scored.salarySocScore,
        cvFitScore: scored.cvFitScore,
        overallScore: scored.overallScore,
        status: scored.status
      }
    });

    await prisma.rejectionReason.deleteMany({ where: { jobId: saved.id } });
    if (scored.rejectionReasons.length > 0) {
      await prisma.rejectionReason.createMany({
        data: scored.rejectionReasons.map((reason) => ({
          jobId: saved.id,
          code: reason.code,
          message: reason.message
        }))
      });
    }
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });

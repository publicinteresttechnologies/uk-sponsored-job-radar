'use server';

import { revalidatePath } from 'next/cache';
import { prisma } from '@/lib/db';
import { generateApplicationPack } from '@/lib/application-pack';

export async function generatePack(jobId: string) {
  const job = await prisma.job.findUniqueOrThrow({ where: { id: jobId } });
  const pack = generateApplicationPack(job);

  await prisma.applicationPack.upsert({
    where: { jobId },
    update: pack,
    create: { jobId, ...pack }
  });

  revalidatePath(`/jobs/${jobId}`);
  revalidatePath('/jobs');
}

export async function markApplied(jobId: string) {
  await prisma.job.update({ where: { id: jobId }, data: { status: 'APPLIED' } });
  revalidatePath('/jobs');
  revalidatePath('/applications');
  revalidatePath(`/jobs/${jobId}`);
}

export async function rejectJob(jobId: string) {
  await prisma.job.update({ where: { id: jobId }, data: { status: 'REJECTED' } });
  await prisma.rejectionReason.create({
    data: {
      jobId,
      code: 'MANUAL_REJECT',
      message: 'Manually rejected during review.'
    }
  });
  revalidatePath('/jobs');
  revalidatePath('/jobs/rejected');
  revalidatePath(`/jobs/${jobId}`);
}

import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'UK Sponsored Job Radar',
  description: 'Human-in-the-loop UK Skilled Worker sponsored-job cockpit.'
};

const nav = [
  ['Dashboard', '/'],
  ['All Jobs', '/jobs'],
  ['Ready', '/jobs/ready'],
  ['Rejected', '/jobs/rejected'],
  ['Applications', '/applications'],
  ['Settings', '/settings']
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="shell">
          <h1>UK Sponsored Job Radar</h1>
          <p className="muted">Visa-first job discovery, scoring and application-pack prep. No blind auto-apply.</p>
          <nav className="nav">
            {nav.map(([label, href]) => (
              <Link href={href} key={href}>
                {label}
              </Link>
            ))}
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}

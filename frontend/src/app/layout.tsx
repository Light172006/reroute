import type { Metadata, Viewport } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import '@/styles/globals.css';
import { Providers } from '@/components/Providers';
import { Navbar } from '@/components/Navbar';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Reroute - A trip plan that fixes itself',
  description:
    'An agentic AI travel planner that builds an itinerary, monitors it, and proposes replans when things change (rain, closures, delays, budget overruns).',
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F6F9' },
    { media: '(prefers-color-scheme: dark)', color: '#0A0A0A' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans min-h-screen flex flex-col bg-page text-text-primary">
        <Providers>
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
        </Providers>
      </body>
    </html>
  );
}

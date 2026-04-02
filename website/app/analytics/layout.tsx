import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Site Analytics | Mirai by VC Labs',
  description: 'Website traffic analytics and visitor insights for Mirai administrators.',
  openGraph: {
    title: 'Site Analytics | Mirai by VC Labs',
    description: 'Website traffic analytics and visitor insights for Mirai administrators.',
    siteName: 'Mirai',
    type: 'website',
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}

'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

function getVisitorId(): string {
  if (typeof window === 'undefined') return '';
  let id = localStorage.getItem('mirai-visitor-id');
  if (!id) {
    id = Math.random().toString(36).substring(2) + Date.now().toString(36);
    localStorage.setItem('mirai-visitor-id', id);
  }
  return id;
}

function getSessionId(): string {
  if (typeof window === 'undefined') return '';
  let id = sessionStorage.getItem('mirai-session-id');
  if (!id) {
    id = Math.random().toString(36).substring(2) + Date.now().toString(36);
    sessionStorage.setItem('mirai-session-id', id);
  }
  return id;
}

export default function Analytics() {
  const pathname = usePathname();

  useEffect(() => {
    if (pathname.startsWith('/api/') || pathname.startsWith('/_next/')) return;

    const data = {
      path: pathname,
      referrer: document.referrer || null,
      visitorId: getVisitorId(),
      sessionId: getSessionId(),
      screenWidth: window.screen.width,
      screenHeight: window.screen.height,
      language: navigator.language || null,
    };

    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/analytics/track', JSON.stringify(data));
    } else {
      fetch('/api/analytics/track', {
        method: 'POST',
        body: JSON.stringify(data),
        keepalive: true,
      }).catch(() => {});
    }
  }, [pathname]);

  return null;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextResponse, type NextRequest } from 'next/server';
import prisma from '@/lib/prisma';

async function geolocate(ip: string) {
  try {
    if (ip === 'unknown' || ip === '127.0.0.1' || ip === '::1' || ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.')) {
      return { city: 'Local', region: 'Local', country: 'Local' };
    }
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await fetch(`http://ip-api.com/json/${ip}?fields=city,regionName,country,status`, {
          signal: AbortSignal.timeout(5000),
        });
        if (!res.ok) continue;
        const data = await res.json();
        if (data.status === 'success' && data.city) {
          return { city: data.city, region: data.regionName || null, country: data.country || null };
        }
      } catch { /* retry */ }
    }
    return { city: null, region: null, country: null };
  } catch {
    return { city: null, region: null, country: null };
  }
}

export async function POST(request: NextRequest) {
  try {
    let body: any;
    try {
      body = await request.json();
    } catch {
      return NextResponse.json({ ok: false, error: 'Invalid JSON' }, { status: 400 });
    }
    const { path, referrer, visitorId, sessionId, screenWidth, screenHeight, language } = body || {};

    if (!path || typeof path !== 'string') {
      return NextResponse.json({ ok: false, error: 'Missing path' }, { status: 400 });
    }

    const ip = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
      || request.headers.get('x-real-ip')
      || 'unknown';
    const userAgent = request.headers.get('user-agent') || '';

    const geo = await geolocate(ip);

    await prisma.pageView.create({
      data: {
        path,
        referrer: referrer || null,
        userAgent,
        ip,
        visitorId: visitorId || null,
        sessionId: sessionId || null,
        screenWidth: screenWidth ? Number(screenWidth) : null,
        screenHeight: screenHeight ? Number(screenHeight) : null,
        language: language || null,
        city: geo.city,
        region: geo.region,
        country: geo.country,
      },
    });

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error('Analytics track error:', error);
    return NextResponse.json({ error: 'Failed to track pageview' }, { status: 500 });
  }
}

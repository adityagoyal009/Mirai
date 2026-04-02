/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextResponse, type NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/prisma';

function serialize(obj: any): any {
  return JSON.parse(JSON.stringify(obj, (_, v) => typeof v === 'bigint' ? Number(v) : v));
}

function parseUserAgents(rows: { userAgent: string; count: number }[]) {
  const devices: Record<string, number> = {};
  const browsers: Record<string, number> = {};
  const oses: Record<string, number> = {};

  for (const row of rows) {
    const ua = row.userAgent || '';
    const count = Number(row.count);

    let device = 'Desktop';
    if (/bot|crawler|spider|crawling/i.test(ua)) device = 'Bot';
    else if (/iPad|Tablet|PlayBook/i.test(ua)) device = 'Tablet';
    else if (/iPhone|Android.*Mobile|Mobile.*Android/i.test(ua)) device = 'Mobile';
    devices[device] = (devices[device] || 0) + count;

    let browser = 'Other';
    if (/bot|crawler|spider/i.test(ua)) browser = 'Bot';
    else if (ua.includes('Edg')) browser = 'Edge';
    else if (ua.includes('Chrome') && !ua.includes('Edg')) browser = 'Chrome';
    else if (ua.includes('Firefox')) browser = 'Firefox';
    else if (ua.includes('Safari') && !ua.includes('Chrome')) browser = 'Safari';
    browsers[browser] = (browsers[browser] || 0) + count;

    let os = 'Other';
    if (ua.includes('Windows')) os = 'Windows';
    else if (ua.includes('Mac OS') || ua.includes('Macintosh')) os = 'macOS';
    else if (ua.includes('Linux') && !ua.includes('Android')) os = 'Linux';
    else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS';
    else if (ua.includes('Android')) os = 'Android';
    oses[os] = (oses[os] || 0) + count;
  }

  const toArray = (obj: Record<string, number>) =>
    Object.entries(obj).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count);

  return { devices: toArray(devices), browsers: toArray(browsers), oses: toArray(oses) };
}

function categorizeReferrer(ref: string | null): string {
  if (!ref) return 'Direct';
  const r = ref.toLowerCase();
  if (/google\.|bing\.|yahoo\.|duckduckgo\.|baidu\.|yandex\./i.test(r)) return 'Organic Search';
  if (/twitter\.|x\.com|facebook\.|instagram\.|linkedin\.|reddit\.|tiktok\.|youtube\./i.test(r)) return 'Social';
  if (r.includes('vclabs.org')) return 'Internal';
  return 'Referral';
}

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions);

  const adminEmails = (process.env.MIRAI_ADMIN_EMAILS || 'adityagoyal009@gmail.com')
    .split(',')
    .map(e => e.trim().toLowerCase())
    .filter(Boolean);

  if (!session?.user?.email || !adminEmails.includes(session.user.email.toLowerCase())) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = new URL(request.url);
  const days = parseInt(searchParams.get('days') || '7');
  const daysParam = `-${days} days`;

  try {
    // Core metrics
    const totalViews: any[] = await prisma.$queryRaw`
      SELECT COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
    `;

    const uniqueVisitors: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT ip) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
    `;

    const topPages: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as views, COUNT(DISTINCT ip) as visitors
      FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY path ORDER BY views DESC LIMIT 20
    `;

    const viewsByDay: any[] = await prisma.$queryRaw`
      SELECT date(created_at/1000, 'unixepoch', '-6 hours') as day, COUNT(*) as views, COUNT(DISTINCT ip) as visitors
      FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY date(created_at/1000, 'unixepoch', '-6 hours') ORDER BY day
    `;

    const topReferrers: any[] = await prisma.$queryRaw`
      SELECT referrer, COUNT(*) as count
      FROM page_views
      WHERE referrer IS NOT NULL AND referrer != ''
        AND created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY referrer ORDER BY count DESC LIMIT 10
    `;

    // Recent visitors
    const recentVisitors: any[] = await prisma.$queryRaw`
      SELECT path, ip, referrer, user_agent as userAgent, city, region, country, screen_width as screenWidth, screen_height as screenHeight, language, created_at as createdAt
      FROM page_views ORDER BY created_at DESC LIMIT 100
    `;

    // Real-time: active visitors in last 5 minutes
    const realTimeActive: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT ip) as count FROM page_views
      WHERE created_at >= (strftime('%s','now','-5 minutes') * 1000)
    `;

    const realTimePages: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now','-5 minutes') * 1000)
      GROUP BY path ORDER BY count DESC LIMIT 10
    `;

    // User growth
    const userGrowth: any[] = await prisma.$queryRaw`
      SELECT date(created_at) as day, COUNT(*) as signups
      FROM users GROUP BY day ORDER BY day
    `;

    const totalUsers: any[] = await prisma.$queryRaw`
      SELECT COUNT(*) as count FROM users
    `;

    // Submission stats (Mirai equivalent of Reports)
    const totalSubmissions: any[] = await prisma.$queryRaw`
      SELECT COUNT(*) as count FROM submissions
    `;

    const submissionsByStatus: any[] = await prisma.$queryRaw`
      SELECT status, COUNT(*) as count FROM submissions GROUP BY status ORDER BY count DESC
    `;

    const submissionsByIndustry: any[] = await prisma.$queryRaw`
      SELECT industry, COUNT(*) as count FROM submissions
      WHERE industry IS NOT NULL AND industry != ''
      GROUP BY industry ORDER BY count DESC
    `;

    const submissionsByStage: any[] = await prisma.$queryRaw`
      SELECT stage, COUNT(*) as count FROM submissions
      WHERE stage IS NOT NULL AND stage != ''
      GROUP BY stage ORDER BY count DESC
    `;

    const submissionsOverTime: any[] = await prisma.$queryRaw`
      SELECT date(created_at) as day, COUNT(*) as count
      FROM submissions GROUP BY day ORDER BY day
    `;

    // Device/Browser/OS
    const userAgents: any[] = await prisma.$queryRaw`
      SELECT user_agent as userAgent, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY user_agent
    `;
    const { devices, browsers, oses } = parseUserAgents(userAgents);

    // New vs returning
    const uniqueVisitorIds: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT visitor_id) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
        AND visitor_id IS NOT NULL AND visitor_id != ''
    `;

    const returningVisitors: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT visitor_id) as count FROM page_views
      WHERE visitor_id IN (
        SELECT visitor_id FROM page_views GROUP BY visitor_id HAVING COUNT(*) > 1
      )
      AND created_at >= (strftime('%s','now',${daysParam}) * 1000)
      AND visitor_id IS NOT NULL AND visitor_id != ''
    `;

    const totalUniqueVids = Number(uniqueVisitorIds[0]?.count || 0);
    const returningCount = Number(returningVisitors[0]?.count || 0);
    const newCount = totalUniqueVids - returningCount;

    // Bounce rate
    const bouncedVisitors: any[] = await prisma.$queryRaw`
      SELECT COUNT(*) as count FROM (
        SELECT visitor_id FROM page_views
        WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
          AND visitor_id IS NOT NULL AND visitor_id != ''
        GROUP BY visitor_id HAVING COUNT(*) = 1
      )
    `;
    const bouncedCount = Number(bouncedVisitors[0]?.count || 0);
    const bounceRate = totalUniqueVids > 0 ? Math.round((bouncedCount / totalUniqueVids) * 100) : 0;

    // Avg pages per session
    const avgPagesPerSession: any[] = await prisma.$queryRaw`
      SELECT AVG(pages) as avg FROM (
        SELECT session_id, COUNT(*) as pages FROM page_views
        WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
          AND session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
      )
    `;

    // Total sessions
    const totalSessions: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT session_id) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
        AND session_id IS NOT NULL AND session_id != ''
    `;

    // Visitor locations from page views
    const visitorLocationsRaw: any[] = await prisma.$queryRaw`
      SELECT country, city, region, ip, user_agent as userAgent, COUNT(*) as views, COUNT(DISTINCT visitor_id) as visitors,
        MIN(created_at) as firstVisit, MAX(created_at) as lastVisit
      FROM page_views
      WHERE country IS NOT NULL AND country != '' AND country != 'Local'
      GROUP BY country, city, region, ip
      ORDER BY lastVisit DESC LIMIT 100
    `;

    const botPatterns = [
      /bot/i, /crawl/i, /spider/i, /scrape/i, /headlesschrome/i,
      /applebot/i, /ahrefsbot/i, /semrushbot/i, /bingbot/i, /googlebot/i,
      /yandexbot/i, /baiduspider/i, /facebookexternalhit/i, /twitterbot/i,
      /linkedinbot/i, /slurp/i, /duckduckbot/i, /ia_archiver/i, /mj12bot/i,
      /dotbot/i, /petalbot/i, /bytespider/i,
    ];
    const botIpPrefixes = ['17.22.', '17.246.', '44.210.', '44.211.', '2a03:2880:'];
    const oldChromePattern = /Chrome\/(\d+)/;

    const visitorLocations = visitorLocationsRaw.map((v: any) => {
      const ua = v.userAgent || '';
      let visitorType = 'Human';
      if (botPatterns.some(p => p.test(ua))) visitorType = 'Bot';
      else if (botIpPrefixes.some(prefix => (v.ip || '').startsWith(prefix))) visitorType = 'Bot';
      else if (ua.includes('HeadlessChrome')) visitorType = 'Bot';
      else {
        const chromeMatch = ua.match(oldChromePattern);
        if (chromeMatch && parseInt(chromeMatch[1]) < 100) visitorType = 'Bot';
      }
      if (visitorType === 'Human' && (v.ip || '').startsWith('2600:3c0')) visitorType = 'Bot';
      return { ...v, userAgent: undefined, visitorType };
    });

    // Acquisition channels
    const allReferrers: any[] = await prisma.$queryRaw`
      SELECT referrer, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY referrer
    `;
    const channels: Record<string, number> = {};
    for (const r of allReferrers) {
      const ch = categorizeReferrer(r.referrer);
      channels[ch] = (channels[ch] || 0) + Number(r.count);
    }
    const acquisitionChannels = Object.entries(channels)
      .filter(([name]) => name !== 'Internal')
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // Screen resolutions
    const screenResolutions: any[] = await prisma.$queryRaw`
      SELECT screen_width as screenWidth, screen_height as screenHeight, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
        AND screen_width IS NOT NULL AND screen_height IS NOT NULL
      GROUP BY screen_width, screen_height
      ORDER BY count DESC LIMIT 10
    `;

    // Languages
    const languages: any[] = await prisma.$queryRaw`
      SELECT language, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
        AND language IS NOT NULL AND language != ''
      GROUP BY language
      ORDER BY count DESC LIMIT 10
    `;

    // Entry pages
    const entryPages: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as count FROM (
        SELECT path, MIN(created_at) as firstHit FROM page_views
        WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
          AND session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
      ) GROUP BY path ORDER BY count DESC LIMIT 10
    `;

    // Exit pages
    const exitPages: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as count FROM (
        SELECT path, MAX(created_at) as lastHit FROM page_views
        WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
          AND session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
      ) GROUP BY path ORDER BY count DESC LIMIT 10
    `;

    // Views by hour of day
    const viewsByHour: any[] = await prisma.$queryRaw`
      SELECT CAST(strftime('%H', created_at/1000, 'unixepoch', '-6 hours') AS INTEGER) as hour, COUNT(*) as count FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY hour ORDER BY hour
    `;

    // Average session duration
    const avgSessionDuration: any[] = await prisma.$queryRaw`
      SELECT AVG(duration) as avg FROM (
        SELECT session_id,
          (((MAX(created_at) - MIN(created_at)) / 1000.0)) * 86400 as duration
        FROM page_views
        WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
          AND session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
        HAVING COUNT(*) > 1
      )
    `;

    // Session details
    const sessionDetails: any[] = await prisma.$queryRaw`
      SELECT
        session_id as sessionId,
        MIN(created_at) as firstSeen,
        MAX(created_at) as lastSeen,
        COUNT(*) as pageCount,
        GROUP_CONCAT(path, '||') as pages,
        (((MAX(created_at) - MIN(created_at)) / 1000.0)) * 86400 as durationSecs,
        ip, city, region, country
      FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
        AND session_id IS NOT NULL AND session_id != ''
      GROUP BY session_id
      HAVING COUNT(*) >= 2
      ORDER BY MAX(created_at) DESC
      LIMIT 50
    `;

    // Conversion funnel: visitors → users → users who submitted
    const funnelSubmitters: any[] = await prisma.$queryRaw`
      SELECT COUNT(DISTINCT user_id) as count FROM submissions
    `;

    // Growing pages
    const previousViews: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as views FROM page_views
      WHERE created_at >= (strftime('%s','now',${'-' + (days * 2) + ' days'}) * 1000)
        AND created_at < (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY path
    `;

    const currentViews: any[] = await prisma.$queryRaw`
      SELECT path, COUNT(*) as views FROM page_views
      WHERE created_at >= (strftime('%s','now',${daysParam}) * 1000)
      GROUP BY path
    `;

    const prevMap: Record<string, number> = {};
    for (const p of previousViews) prevMap[p.path] = Number(p.views);
    const growingPages = currentViews
      .map(p => ({
        path: p.path,
        current: Number(p.views),
        previous: prevMap[p.path] || 0,
        growth: prevMap[p.path] ? Math.round(((Number(p.views) - prevMap[p.path]) / prevMap[p.path]) * 100) : 100,
      }))
      .filter(p => p.current > 1)
      .sort((a, b) => b.growth - a.growth)
      .slice(0, 10);

    return NextResponse.json(serialize({
      period: `${days} days`,
      totalViews: totalViews[0]?.count || 0,
      uniqueVisitors: uniqueVisitors[0]?.count || 0,
      topPages,
      viewsByDay,
      topReferrers,
      recentVisitors,
      // Real-time
      realTimeActive: realTimeActive[0]?.count || 0,
      realTimePages,
      // Users & Submissions
      userGrowth,
      totalUsers: totalUsers[0]?.count || 0,
      totalSubmissions: totalSubmissions[0]?.count || 0,
      submissionsByStatus,
      submissionsByIndustry,
      submissionsByStage,
      submissionsOverTime,
      // Breakdown
      devices,
      browsers,
      oses,
      // Engagement
      newVisitors: newCount,
      returningVisitors: returningCount,
      bounceRate,
      avgPagesPerSession: Number(avgPagesPerSession[0]?.avg || 0).toFixed(1),
      totalSessions: totalSessions[0]?.count || 0,
      // Geographic
      visitorLocations,
      // Acquisition
      acquisitionChannels,
      // Tech
      screenResolutions: screenResolutions.map(r => ({
        name: `${r.screenWidth}x${r.screenHeight}`,
        count: Number(r.count),
      })),
      languages: languages.map(l => ({ name: l.language, count: Number(l.count) })),
      // Navigation
      entryPages,
      exitPages,
      viewsByHour,
      // Session metrics
      avgSessionDuration: Math.round(Number(avgSessionDuration[0]?.avg || 0)),
      conversionFunnel: {
        visitors: uniqueVisitors[0]?.count || 0,
        users: totalUsers[0]?.count || 0,
        submitters: funnelSubmitters[0]?.count || 0,
      },
      growingPages,
      sessionDetails: sessionDetails.map((s: any) => ({
        sessionId: s.sessionId,
        location: [s.city, s.region, s.country].filter(Boolean).join(', '),
        pageCount: Number(s.pageCount),
        durationSecs: Math.round(Number(s.durationSecs || 0)),
        duration: (() => {
          const secs = Math.round(Number(s.durationSecs || 0));
          if (secs < 60) return `${secs}s`;
          const mins = Math.floor(secs / 60);
          const rem = secs % 60;
          return rem ? `${mins}m ${rem}s` : `${mins}m`;
        })(),
        pages: (s.pages || '').split('||').filter((p: string) => p),
        firstSeen: s.firstSeen,
        lastSeen: s.lastSeen,
        ip: s.ip,
      })),
    }));
  } catch (error) {
    console.error('Analytics error:', error);
    return NextResponse.json({ error: 'Failed to fetch analytics' }, { status: 500 });
  }
}

'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

/* ── Icons (inline SVG helpers to avoid lucide dependency issues) ── */
function Icon({ d, className = '' }: { d: string; className?: string }) {
  return (
    <svg className={`w-5 h-5 ${className}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

const ICONS = {
  barChart: 'M12 20V10M18 20V4M6 20v-4',
  eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z',
  users: 'M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75',
  zap: 'M13 2L3 14h9l-1 8 10-12h-9l1-8',
  timer: 'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 6v6l4 2',
  arrowLR: 'M7 16l-4-4 4-4M17 8l4 4-4 4M3 12h18',
  fileText: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8',
  userPlus: 'M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M8.5 11a4 4 0 100-8 4 4 0 000 8zM20 8v6M23 11h-6',
  globe: 'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10A15.3 15.3 0 0112 2',
  trendingUp: 'M23 6l-9.5 9.5-5-5L1 18',
  clock: 'M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zM12 6v6l4 2',
  mapPin: 'M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  monitor: 'M2 3h20v14H2zM8 21h8M12 17v4',
  smartphone: 'M7 2h10a1 1 0 011 1v18a1 1 0 01-1 1H7a1 1 0 01-1-1V3a1 1 0 011-1zM11 18h2',
  laptop: 'M4 5h16a1 1 0 011 1v10H3V6a1 1 0 011-1zM1 19h22',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  doorOpen: 'M13 4h3a2 2 0 012 2v14M5 12h6M8 9l3 3-3 3',
  doorClosed: 'M13 4h3a2 2 0 012 2v14M3 12h8M8 9l3 3-3 3',
  arrowUp: 'M7 17l5-5 5 5M7 7l5 5 5-5',
  arrowDown: 'M7 7l5 5 5-5M7 17l5-5 5-5',
  refresh: 'M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15',
  login: 'M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4M10 17l5-5-5-5M15 12H3',
};

/* ── Types ── */
interface NameCount { name: string; count: number; }

interface AnalyticsData {
  period: string;
  totalViews: number;
  uniqueVisitors: number;
  topPages: { path: string; views: number; visitors: number }[];
  viewsByDay: { day: string; views: number; visitors: number }[];
  topReferrers: { referrer: string; count: number }[];
  recentVisitors: { path: string; ip: string; referrer: string; userAgent: string; city: string; region: string; country: string; screenWidth: number; screenHeight: number; language: string; createdAt: string }[];
  visitorLocations: { country: string; city: string; region: string; ip: string; views: number; visitors: number; firstVisit: string; lastVisit: string; visitorType: string }[];
  realTimeActive: number;
  realTimePages: { path: string; count: number }[];
  userGrowth: { day: string; signups: number }[];
  totalUsers: number;
  totalSubmissions: number;
  submissionsByStatus: { status: string; count: number }[];
  submissionsByIndustry: { industry: string; count: number }[];
  submissionsByStage: { stage: string; count: number }[];
  submissionsOverTime: { day: string; count: number }[];
  devices: NameCount[];
  browsers: NameCount[];
  oses: NameCount[];
  newVisitors: number;
  returningVisitors: number;
  bounceRate: number;
  avgPagesPerSession: string;
  totalSessions: number;
  acquisitionChannels: NameCount[];
  screenResolutions: NameCount[];
  languages: NameCount[];
  entryPages: { path: string; count: number }[];
  exitPages: { path: string; count: number }[];
  viewsByHour: { hour: number; count: number }[];
  avgSessionDuration: number;
  conversionFunnel: { visitors: number; users: number; submitters: number };
  growingPages: { path: string; current: number; previous: number; growth: number }[];
  sessionDetails: { sessionId: string; location: string; pageCount: number; durationSecs: number; duration: string; pages: string[]; firstSeen: string; lastSeen: string; ip: string }[];
}

const ADMIN_EMAILS = ['adityagoyal009@gmail.com', 'vclabsai@gmail.com'];

const CHANNEL_COLORS: Record<string, string> = {
  'Direct': '#196cff', 'Organic Search': '#34c7a0', 'Social': '#9b5cff', 'Referral': '#f3b13f',
};

const STATUS_COLORS: Record<string, string> = {
  queued: '#196cff', reviewing: '#f3b13f', report_sent: '#34c7a0', archived: '#6e7f97',
};

const TABS = ['Overview', 'Audience', 'Acquisition', 'Behavior', 'Sessions', 'Submissions'] as const;
type Tab = typeof TABS[number];

/* ── Helpers ── */
function getBrowser(ua: string): string {
  if (!ua) return 'Unknown';
  if (/bot|crawler|spider/i.test(ua)) return 'Bot';
  if (ua.includes('Edg')) return 'Edge';
  if (ua.includes('Chrome') && !ua.includes('Edg')) return 'Chrome';
  if (ua.includes('Firefox')) return 'Firefox';
  if (ua.includes('Safari') && !ua.includes('Chrome')) return 'Safari';
  return 'Other';
}

function getOS(ua: string): string {
  if (!ua) return 'Unknown';
  if (ua.includes('Windows')) return 'Windows';
  if (ua.includes('Mac OS')) return 'macOS';
  if (ua.includes('Linux')) return 'Linux';
  if (ua.includes('iPhone') || ua.includes('iPad')) return 'iOS';
  if (ua.includes('Android')) return 'Android';
  return 'Other';
}

function parseDate(val: unknown): Date {
  if (!val) return new Date(0);
  const s = String(val);
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(s)) return new Date(s.replace(' ', 'T') + 'Z');
  const d = new Date(s);
  return isNaN(d.getTime()) ? new Date(Number(s)) : d;
}

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = parseDate(dateStr);
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

/* ── Reusable Components ── */

function HBarChart({ items, colorMap, maxItems = 10 }: { items: NameCount[]; colorMap?: Record<string, string>; maxItems?: number }) {
  const visible = items.slice(0, maxItems);
  const max = Math.max(...visible.map(i => i.count), 1);
  const total = visible.reduce((s, i) => s + i.count, 0);

  return (
    <div className="space-y-2.5">
      {visible.map((item, i) => {
        const pct = total > 0 ? Math.round((item.count / total) * 100) : 0;
        const color = colorMap?.[item.name.toLowerCase()] || colorMap?.[item.name] || 'var(--blue)';
        return (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-[var(--ink)] capitalize">{item.name}</span>
              <span className="text-[var(--ink-soft)]">{item.count} ({pct}%)</span>
            </div>
            <div className="w-full bg-[#e7edf5] rounded-full h-2">
              <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${(item.count / max) * 100}%`, backgroundColor: color }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MiniBarChart({ data, valueKey, color = 'var(--blue)' }: { data: Record<string, unknown>[]; valueKey: string; color?: string }) {
  if (!data || data.length === 0) return <p className="text-[var(--ink-soft)] text-center py-8 text-sm">No data available</p>;
  const max = Math.max(...data.map(d => Number(d[valueKey])), 1);
  return (
    <div className="flex items-end gap-1 h-36">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
          <span className="text-[10px] text-[var(--ink-faint)] opacity-0 group-hover:opacity-100 transition-opacity">{Number(d[valueKey])}</span>
          <div className="w-full rounded-t-sm min-h-[2px] transition-all duration-300 group-hover:opacity-80" style={{ height: `${(Number(d[valueKey]) / max) * 120}px`, backgroundColor: color, opacity: 0.75 }} />
          <span className="text-[9px] text-[var(--ink-faint)] truncate w-full text-center">
            {(d as Record<string, unknown>).day ? new Date(String((d as Record<string, unknown>).day) + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : (d as Record<string, unknown>).hour !== undefined ? `${(d as Record<string, unknown>).hour}:00` : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[var(--card)] backdrop-blur-sm rounded-[24px] border border-[var(--line)] p-6 shadow-sm hover:shadow-md transition-shadow duration-200 ${className}`}>
      {children}
    </div>
  );
}

function SectionTitle({ icon, children, color = 'text-[var(--blue)]' }: { icon: string; children: React.ReactNode; color?: string }) {
  return (
    <h2 className="text-lg font-bold text-[var(--ink)] mb-4 flex items-center gap-2 tracking-tight">
      <Icon d={icon} className={`w-5 h-5 ${color}`} />
      {children}
    </h2>
  );
}

function StatCard({ icon, label, value, gradient, suffix = '', subtitle }: { icon: string; label: string; value: number | string; gradient: string; suffix?: string; subtitle?: string }) {
  return (
    <div className={`rounded-[18px] border border-[var(--line)] p-5 transition-transform duration-200 hover:translate-y-[-2px] hover:shadow-md ${gradient}`}>
      <Icon d={icon} className="w-5 h-5 mb-2 opacity-70" />
      <div className="text-2xl font-bold tracking-tight">{typeof value === 'number' ? value.toLocaleString() : value}{suffix}</div>
      <div className="text-sm opacity-65 mt-0.5">{label}</div>
      {subtitle && <div className="text-xs opacity-45 mt-1">{subtitle}</div>}
    </div>
  );
}

function ConversionFunnel({ funnel }: { funnel: { visitors: number; users: number; submitters: number } }) {
  const steps = [
    { label: 'Visitors', value: funnel.visitors, color: 'var(--blue)' },
    { label: 'Signed Up', value: funnel.users, color: 'var(--coral)' },
    { label: 'Submitted Reports', value: funnel.submitters, color: 'var(--mint)' },
  ];
  const max = Math.max(...steps.map(s => s.value), 1);

  return (
    <div className="space-y-4">
      {steps.map((step, i) => {
        const rate = i > 0 && steps[i - 1].value > 0
          ? Math.round((step.value / steps[i - 1].value) * 100)
          : 100;
        return (
          <div key={i}>
            <div className="flex justify-between text-sm mb-1.5">
              <span className="text-[var(--ink)] font-medium">{step.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-[var(--ink)] font-bold">{step.value}</span>
                {i > 0 && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-[#e7edf5] text-[var(--ink-soft)]">
                    {rate}% conversion
                  </span>
                )}
              </div>
            </div>
            <div className="w-full bg-[#e7edf5] rounded-full h-3">
              <div className="h-3 rounded-full transition-all duration-700" style={{
                width: `${(step.value / max) * 100}%`,
                backgroundColor: step.color,
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Main Page Component ── */
export default function SiteAnalyticsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('Overview');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (status === 'unauthenticated') router.push('/');
  }, [status, router]);

  const fetchData = useCallback(() => {
    if (status !== 'authenticated') return;
    if (!session?.user?.email || !ADMIN_EMAILS.includes(session.user.email.toLowerCase())) {
      router.push('/');
      return;
    }
    fetch(`/api/analytics?days=${days}`)
      .then(res => res.json())
      .then(d => {
        if (d.error) setError(d.error);
        else { setData(d); setLastRefresh(new Date()); }
        setLoading(false);
      })
      .catch(() => { setError('Failed to load analytics'); setLoading(false); });
  }, [status, session, days, router]);

  useEffect(() => {
    setLoading(true);
    fetchData();
  }, [fetchData]);

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      setCountdown(30);
      intervalRef.current = setInterval(() => {
        fetchData();
        setCountdown(30);
      }, 30000);
      countdownRef.current = setInterval(() => {
        setCountdown(c => c > 0 ? c - 1 : 30);
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoRefresh, fetchData]);

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--blue)]" />
          <span className="text-sm text-[var(--ink-soft)]">Loading analytics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-[18px] p-6 text-red-700 text-center">
          <Icon d={ICONS.shield} className="w-8 h-8 mx-auto mb-2 text-red-400" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const maxViews = Math.max(...(data.viewsByDay?.map(d => d.views) || [0]), 1);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[var(--ink)] flex items-center gap-3 tracking-tight">
            <Icon d={ICONS.barChart} className="w-8 h-8 text-[var(--blue)]" />
            Site Analytics
          </h1>
          <p className="text-[var(--ink-soft)] mt-1 text-sm">
            {lastRefresh ? `Updated ${timeAgo(lastRefresh.toISOString())}` : 'Loading...'}
          </p>
        </div>
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* Auto-refresh */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${
              autoRefresh
                ? 'bg-[var(--mint)]/10 text-[var(--mint)] border-[var(--mint)]/30'
                : 'bg-white/80 text-[var(--ink-soft)] border-[var(--line)]'
            }`}
          >
            <Icon d={ICONS.refresh} className={`w-3.5 h-3.5 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? `Live · ${countdown}s` : 'Auto-refresh'}
          </button>

          {/* Manual refresh */}
          <button onClick={() => { setLoading(true); fetchData(); }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-white/80 text-[var(--ink-soft)] border border-[var(--line)] hover:bg-white transition-colors">
            <Icon d={ICONS.refresh} className="w-3.5 h-3.5" />
            Refresh
          </button>

          {/* Day selector */}
          <div className="flex rounded-full border border-[var(--line)] overflow-hidden bg-white/80">
            {[
              { v: 7, l: '7d' },
              { v: 14, l: '14d' },
              { v: 30, l: '30d' },
              { v: 90, l: '90d' },
            ].map(({ v, l }) => (
              <button key={v} onClick={() => setDays(v)}
                className={`px-3 py-1.5 text-xs font-bold transition-all ${
                  days === v
                    ? 'bg-gradient-to-br from-[var(--blue)] to-[#4b95ff] text-white'
                    : 'text-[var(--ink-soft)] hover:bg-[#e7edf5]'
                }`}>
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Real-Time Banner ── */}
      <div className="hero-gradient text-white rounded-[24px] p-5 mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Icon d={ICONS.activity} className="w-6 h-6 text-[var(--mint)]" />
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-[var(--mint)] rounded-full animate-pulse" />
          </div>
          <div>
            <span className="text-2xl font-bold">{data.realTimeActive}</span>
            <span className="text-white/60 ml-2 text-sm">active right now</span>
          </div>
        </div>
        {data.realTimePages && data.realTimePages.length > 0 && (
          <div className="text-sm text-white/50 hidden sm:flex gap-3">
            {data.realTimePages.slice(0, 3).map((p, i) => (
              <span key={i} className="inline-flex items-center gap-1">
                <span className="font-mono text-xs text-white/70">{p.path}</span>
                <span className="text-[var(--mint)] font-bold">{Number(p.count)}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── Tab Navigation ── */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1 border-b border-[var(--line)]">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-bold rounded-t-lg transition-all whitespace-nowrap ${
              tab === t
                ? 'text-[var(--blue)] bg-[var(--blue)]/10 border-b-2 border-[var(--blue)]'
                : 'text-[var(--ink-soft)] hover:text-[var(--ink)] hover:bg-[#e7edf5]/60'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ═══════════════ OVERVIEW ═══════════════ */}
      {tab === 'Overview' && (
        <>
          {/* Stat Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <StatCard icon={ICONS.eye} label="Total Views" value={data.totalViews} gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" />
            <StatCard icon={ICONS.users} label="Unique Visitors" value={data.uniqueVisitors} gradient="bg-gradient-to-br from-emerald-50 to-emerald-100/50 text-[var(--mint)]" />
            <StatCard icon={ICONS.zap} label="Sessions" value={data.totalSessions} gradient="bg-gradient-to-br from-purple-50 to-purple-100/50 text-purple-600" />
            <StatCard icon={ICONS.timer} label="Avg Duration" value={formatDuration(data.avgSessionDuration)} gradient="bg-gradient-to-br from-orange-50 to-orange-100/50 text-[var(--coral)]" subtitle={data.avgSessionDuration > 0 ? 'per session' : 'not enough data'} />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={ICONS.arrowLR} label="Bounce Rate" value={data.bounceRate} suffix="%" gradient="bg-gradient-to-br from-emerald-50 to-emerald-100/50 text-[var(--mint)]" />
            <StatCard icon={ICONS.fileText} label="Pages/Session" value={data.avgPagesPerSession} gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" />
            <StatCard icon={ICONS.userPlus} label="Total Users" value={data.totalUsers} gradient="bg-gradient-to-br from-sky-50 to-sky-100/50 text-sky-600" />
            <StatCard icon={ICONS.fileText} label="Submissions" value={data.totalSubmissions} gradient="bg-gradient-to-br from-amber-50 to-amber-100/50 text-[var(--amber)]" />
          </div>

          {/* Views Over Time */}
          <Card className="mb-8">
            <SectionTitle icon={ICONS.trendingUp}>Views Over Time</SectionTitle>
            {data.viewsByDay.length === 0 ? (
              <p className="text-[var(--ink-soft)] text-center py-8">No data for this period</p>
            ) : (
              <div className="flex items-end gap-1 h-48">
                {data.viewsByDay.map((d, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group cursor-default">
                    <span className="text-xs text-[var(--ink-soft)] opacity-0 group-hover:opacity-100 transition-opacity">
                      {d.views} views · {d.visitors} visitors
                    </span>
                    <div className="w-full chart-bar min-h-[2px] transition-all duration-300 group-hover:opacity-80" style={{ height: `${(d.views / maxViews) * 160}px` }} />
                    <span className="text-[10px] text-[var(--ink-faint)] truncate w-full text-center">
                      {new Date(d.day + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Conversion Funnel + Growing Pages */}
          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <SectionTitle icon={ICONS.trendingUp} color="text-purple-600">Conversion Funnel</SectionTitle>
              <ConversionFunnel funnel={data.conversionFunnel} />
            </Card>
            <Card>
              <SectionTitle icon={ICONS.trendingUp} color="text-[var(--mint)]">Trending Pages</SectionTitle>
              {!data.growingPages || data.growingPages.length === 0 ? (
                <p className="text-[var(--ink-soft)] text-sm">Need 2+ periods of data</p>
              ) : (
                <div className="space-y-3">
                  {data.growingPages.slice(0, 8).map((p, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-[var(--ink)] font-mono truncate max-w-[200px]">{p.path}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-[var(--ink-soft)]">{p.previous} → {p.current}</span>
                        <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${
                          p.growth > 0 ? 'bg-green-50 text-green-700' :
                          p.growth < 0 ? 'bg-red-50 text-red-700' :
                          'bg-gray-100 text-[var(--ink-soft)]'
                        }`}>
                          {p.growth > 0 ? '↑' : p.growth < 0 ? '↓' : '–'}{Math.abs(p.growth)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Views by Hour */}
          {data.viewsByHour && data.viewsByHour.length > 0 && (
            <Card className="mb-8">
              <SectionTitle icon={ICONS.clock}>Traffic by Hour (CST)</SectionTitle>
              <MiniBarChart data={data.viewsByHour.map(h => ({ ...h, day: undefined }))} valueKey="count" color="var(--sky)" />
              <div className="flex justify-between text-[10px] text-[var(--ink-faint)] mt-1 px-1">
                <span>12 AM</span><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>11 PM</span>
              </div>
            </Card>
          )}
        </>
      )}

      {/* ═══════════════ AUDIENCE ═══════════════ */}
      {tab === 'Audience' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={ICONS.users} label="New Visitors" value={data.newVisitors} gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" />
            <StatCard icon={ICONS.users} label="Returning" value={data.returningVisitors} gradient="bg-gradient-to-br from-emerald-50 to-emerald-100/50 text-[var(--mint)]" />
            <StatCard icon={ICONS.userPlus} label="Total Users" value={data.totalUsers} gradient="bg-gradient-to-br from-sky-50 to-sky-100/50 text-sky-600" />
            <StatCard icon={ICONS.zap} label="Sessions" value={data.totalSessions} gradient="bg-gradient-to-br from-purple-50 to-purple-100/50 text-purple-600" />
          </div>

          {/* New vs Returning */}
          <Card className="mb-8">
            <SectionTitle icon={ICONS.users} color="text-[var(--mint)]">New vs Returning Visitors</SectionTitle>
            {(data.newVisitors + data.returningVisitors) === 0 ? (
              <p className="text-[var(--ink-soft)] text-sm">No visitor data yet</p>
            ) : (
              <HBarChart items={[{ name: 'New', count: data.newVisitors }, { name: 'Returning', count: data.returningVisitors }]} colorMap={{ new: 'var(--blue)', returning: 'var(--mint)' }} />
            )}
          </Card>

          {/* User Growth */}
          <Card className="mb-8">
            <SectionTitle icon={ICONS.userPlus} color="text-sky-600">User Signups Over Time</SectionTitle>
            <MiniBarChart data={data.userGrowth} valueKey="signups" color="var(--blue)" />
          </Card>

          {/* Device / Browser / OS */}
          <div className="grid lg:grid-cols-3 gap-6 mb-8">
            <Card>
              <SectionTitle icon={ICONS.laptop}>Devices</SectionTitle>
              {data.devices.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No data</p> : (
                <HBarChart items={data.devices} colorMap={{ desktop: 'var(--blue)', mobile: 'var(--mint)', tablet: 'var(--ink-faint)', bot: 'var(--coral)' }} />
              )}
            </Card>
            <Card>
              <SectionTitle icon={ICONS.globe} color="text-[var(--mint)]">Browsers</SectionTitle>
              {data.browsers.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No data</p> : (
                <HBarChart items={data.browsers} colorMap={{ chrome: 'var(--blue)', safari: 'var(--mint)', firefox: 'var(--amber)', edge: 'var(--ink-faint)', bot: 'var(--coral)', other: '#92400E' }} />
              )}
            </Card>
            <Card>
              <SectionTitle icon={ICONS.monitor} color="text-sky-600">Operating Systems</SectionTitle>
              {data.oses.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No data</p> : (
                <HBarChart items={data.oses} colorMap={{ windows: 'var(--blue)', macos: 'var(--ink)', linux: 'var(--amber)', ios: 'var(--mint)', android: '#22C55E', other: 'var(--ink-faint)' }} />
              )}
            </Card>
          </div>

          {/* Screen Resolution / Languages */}
          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <SectionTitle icon={ICONS.monitor} color="text-purple-600">Screen Resolutions</SectionTitle>
              {data.screenResolutions.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No data yet</p> : (
                <HBarChart items={data.screenResolutions} colorMap={{}} />
              )}
            </Card>
            <Card>
              <SectionTitle icon={ICONS.globe} color="text-sky-600">Languages</SectionTitle>
              {data.languages.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No data yet</p> : (
                <HBarChart items={data.languages} colorMap={{}} />
              )}
            </Card>
          </div>

          {/* Visitor Locations */}
          {data.visitorLocations && data.visitorLocations.length > 0 && (
            <Card className="mb-8">
              <SectionTitle icon={ICONS.globe} color="text-[var(--blue)]">Visitor Locations</SectionTitle>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[var(--ink-soft)] border-b border-[var(--line)]">
                      <th className="pb-2 font-bold">Location</th>
                      <th className="pb-2 font-bold">IP</th>
                      <th className="pb-2 font-bold">Type</th>
                      <th className="pb-2 font-bold">First Visit</th>
                      <th className="pb-2 font-bold">Last Visit</th>
                      <th className="pb-2 font-bold text-right">Views</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e7edf5]">
                    {data.visitorLocations.map((loc, i) => {
                      const first = parseDate(loc.firstVisit);
                      const last = parseDate(loc.lastVisit);
                      return (
                        <tr key={i} className="text-[var(--ink)] hover:bg-[#f0f4fa] transition-colors">
                          <td className="py-2">
                            <div className="flex items-center gap-1.5">
                              <Icon d={ICONS.mapPin} className="w-3.5 h-3.5 text-[var(--ink-faint)] shrink-0" />
                              <span>{loc.city && loc.region ? `${loc.city}, ${loc.region}` : loc.country}</span>
                            </div>
                            {loc.city && <span className="text-xs text-[var(--ink-soft)] ml-5">{loc.country}</span>}
                          </td>
                          <td className="py-2 font-mono text-xs text-[var(--ink-soft)]">{loc.ip}</td>
                          <td className="py-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                              loc.visitorType === 'Bot'
                                ? 'bg-red-50 text-red-700'
                                : 'bg-green-50 text-green-700'
                            }`}>
                              {loc.visitorType || 'Human'}
                            </span>
                          </td>
                          <td className="py-2 text-xs whitespace-nowrap">{first.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {first.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}</td>
                          <td className="py-2 text-xs whitespace-nowrap">{last.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} {last.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })}</td>
                          <td className="py-2 text-right font-bold">{loc.views}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}

      {/* ═══════════════ ACQUISITION ═══════════════ */}
      {tab === 'Acquisition' && (
        <>
          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <SectionTitle icon={ICONS.globe} color="text-[var(--mint)]">Acquisition Channels</SectionTitle>
              {data.acquisitionChannels.length === 0 ? (
                <p className="text-[var(--ink-soft)] text-sm">No data yet</p>
              ) : (
                <HBarChart items={data.acquisitionChannels} colorMap={CHANNEL_COLORS} />
              )}
            </Card>
            <Card>
              <SectionTitle icon={ICONS.globe}>Traffic Sources</SectionTitle>
              {data.topReferrers.length === 0 ? (
                <p className="text-[var(--ink-soft)] text-sm">No referrer data yet</p>
              ) : (
                <div className="space-y-3">
                  {data.topReferrers.map((r, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-[var(--ink)] truncate max-w-[250px]">{r.referrer}</span>
                      <span className="text-sm font-bold text-[var(--ink-soft)]">{r.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </>
      )}

      {/* ═══════════════ BEHAVIOR ═══════════════ */}
      {tab === 'Behavior' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <StatCard icon={ICONS.eye} label="Total Views" value={data.totalViews} gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" />
            <StatCard icon={ICONS.arrowLR} label="Bounce Rate" value={data.bounceRate} suffix="%" gradient="bg-gradient-to-br from-emerald-50 to-emerald-100/50 text-[var(--mint)]" />
            <StatCard icon={ICONS.fileText} label="Pages/Session" value={data.avgPagesPerSession} gradient="bg-gradient-to-br from-purple-50 to-purple-100/50 text-purple-600" />
            <StatCard icon={ICONS.timer} label="Avg Duration" value={formatDuration(data.avgSessionDuration)} gradient="bg-gradient-to-br from-orange-50 to-orange-100/50 text-[var(--coral)]" />
          </div>

          {/* Top Pages */}
          <Card className="mb-8">
            <SectionTitle icon={ICONS.eye}>Top Pages</SectionTitle>
            <div className="space-y-2">
              {data.topPages.map((p, i) => (
                <div key={i} className="flex items-center justify-between hover:bg-[#f0f4fa] px-3 py-2 rounded-lg transition-colors">
                  <span className="text-sm text-[var(--ink)] font-mono">{p.path}</span>
                  <div className="flex gap-4 text-sm">
                    <span className="text-[var(--ink-soft)]">{p.views} views</span>
                    <span className="text-[var(--blue)] font-bold">{p.visitors} visitors</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Entry/Exit Pages */}
          <div className="grid lg:grid-cols-2 gap-6 mb-8">
            <Card>
              <SectionTitle icon={ICONS.doorOpen} color="text-[var(--mint)]">Top Entry Pages</SectionTitle>
              {!data.entryPages || data.entryPages.length === 0 ? (
                <p className="text-[var(--ink-soft)] text-sm">No data</p>
              ) : (
                <div className="space-y-2">
                  {data.entryPages.map((p, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-[var(--ink)] font-mono">{p.path}</span>
                      <span className="text-sm font-bold text-[var(--mint)]">{Number(p.count)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            <Card>
              <SectionTitle icon={ICONS.doorClosed} color="text-[var(--coral)]">Top Exit Pages</SectionTitle>
              {!data.exitPages || data.exitPages.length === 0 ? (
                <p className="text-[var(--ink-soft)] text-sm">No data</p>
              ) : (
                <div className="space-y-2">
                  {data.exitPages.map((p, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-[var(--ink)] font-mono">{p.path}</span>
                      <span className="text-sm font-bold text-[var(--coral)]">{Number(p.count)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Recent Visitors */}
          <Card>
            <SectionTitle icon={ICONS.eye} color="text-[var(--mint)]">Recent Visitors</SectionTitle>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[var(--ink-soft)] border-b border-[var(--line)]">
                    <th className="pb-2 font-bold">Page</th>
                    <th className="pb-2 font-bold">IP</th>
                    <th className="pb-2 font-bold">Location</th>
                    <th className="pb-2 font-bold">Device</th>
                    <th className="pb-2 font-bold">When</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e7edf5]">
                  {data.recentVisitors.slice(0, 50).map((v, i) => (
                    <tr key={i} className="text-[var(--ink)] hover:bg-[#f0f4fa] transition-colors">
                      <td className="py-2 font-mono text-xs">{v.path}</td>
                      <td className="py-2 font-mono text-xs text-[var(--ink-soft)]">{v.ip}</td>
                      <td className="py-2 text-xs">
                        {v.city && v.region && v.city !== 'Local' ? (
                          <span className="flex items-center gap-1"><Icon d={ICONS.mapPin} className="w-3 h-3 text-[var(--ink-faint)]" />{v.city}, {v.region}</span>
                        ) : <span className="text-[var(--ink-faint)]">–</span>}
                      </td>
                      <td className="py-2 text-xs">{getBrowser(v.userAgent)} / {getOS(v.userAgent)}</td>
                      <td className="py-2 text-xs text-[var(--ink-soft)] whitespace-nowrap">{timeAgo(v.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════════ SESSIONS ═══════════════ */}
      {tab === 'Sessions' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            <StatCard icon={ICONS.zap} label="Multi-Page Sessions" value={data.sessionDetails?.length || 0} gradient="bg-gradient-to-br from-purple-50 to-purple-100/50 text-purple-600" />
            <StatCard icon={ICONS.clock} label="Avg Duration" value={formatDuration(data.avgSessionDuration)} gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" />
            <StatCard icon={ICONS.eye} label="Avg Pages/Session" value={data.avgPagesPerSession} gradient="bg-gradient-to-br from-emerald-50 to-emerald-100/50 text-[var(--mint)]" />
          </div>
          <Card>
            <h3 className="text-[var(--ink)] font-bold mb-4 tracking-tight">Visitor Sessions (2+ pages)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[var(--ink-soft)] border-b border-[var(--line)]">
                    <th className="text-left py-2 px-3 font-bold">Location</th>
                    <th className="text-left py-2 px-3 font-bold">Pages</th>
                    <th className="text-left py-2 px-3 font-bold">Time Spent</th>
                    <th className="text-left py-2 px-3 font-bold">Pages Visited</th>
                    <th className="text-left py-2 px-3 font-bold">Last Active</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.sessionDetails || []).map((s, i) => (
                    <tr key={s.sessionId || i} className="border-b border-[#e7edf5] hover:bg-[#f0f4fa] transition-colors">
                      <td className="py-3 px-3">
                        <span className="text-[var(--ink)] font-medium">{s.location || 'Unknown'}</span>
                        <div className="text-[var(--ink-faint)] text-xs">{s.ip}</div>
                      </td>
                      <td className="py-3 px-3 text-[var(--blue)] font-bold">{s.pageCount}</td>
                      <td className="py-3 px-3">
                        <span className={`font-bold ${s.durationSecs > 120 ? 'text-[var(--mint)]' : s.durationSecs > 30 ? 'text-[var(--amber)]' : 'text-[var(--ink-soft)]'}`}>
                          {s.duration}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex flex-wrap gap-1">
                          {s.pages.map((p, j) => (
                            <span key={j} className="inline-block bg-[#e7edf5] text-[var(--ink)] text-xs px-2 py-0.5 rounded-full font-mono">
                              {p}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-[var(--ink-soft)] text-xs whitespace-nowrap">
                        {new Date(s.lastSeen).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                      </td>
                    </tr>
                  ))}
                  {(!data.sessionDetails || data.sessionDetails.length === 0) && (
                    <tr><td colSpan={5} className="py-8 text-center text-[var(--ink-soft)]">No multi-page sessions in this period</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════════ SUBMISSIONS ═══════════════ */}
      {tab === 'Submissions' && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            <StatCard icon={ICONS.fileText} label="Total Submissions" value={data.totalSubmissions} gradient="bg-gradient-to-br from-amber-50 to-amber-100/50 text-[var(--amber)]" />
            <StatCard icon={ICONS.users} label="Unique Submitters" value={data.conversionFunnel.submitters} gradient="bg-gradient-to-br from-purple-50 to-purple-100/50 text-purple-600" />
            <StatCard icon={ICONS.trendingUp} label="Submit Rate" value={data.totalUsers > 0 ? Math.round((data.conversionFunnel.submitters / data.totalUsers) * 100) : 0} suffix="%" gradient="bg-gradient-to-br from-blue-50 to-blue-100/50 text-[var(--blue)]" subtitle="users who submitted" />
          </div>

          <Card className="mb-8">
            <SectionTitle icon={ICONS.fileText}>Submission Analytics</SectionTitle>
            <div className="grid lg:grid-cols-3 gap-8">
              <div>
                <h3 className="text-sm font-bold text-[var(--ink-soft)] mb-3 uppercase tracking-wide">By Status</h3>
                {!data.submissionsByStatus || data.submissionsByStatus.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No submissions yet</p> : (
                  <HBarChart items={data.submissionsByStatus.map(r => ({ name: r.status, count: Number(r.count) }))} colorMap={STATUS_COLORS} />
                )}
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--ink-soft)] mb-3 uppercase tracking-wide">By Industry</h3>
                {!data.submissionsByIndustry || data.submissionsByIndustry.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No submissions yet</p> : (
                  <HBarChart items={data.submissionsByIndustry.map(r => ({ name: r.industry, count: Number(r.count) }))} colorMap={{}} />
                )}
              </div>
              <div>
                <h3 className="text-sm font-bold text-[var(--ink-soft)] mb-3 uppercase tracking-wide">By Stage</h3>
                {!data.submissionsByStage || data.submissionsByStage.length === 0 ? <p className="text-[var(--ink-soft)] text-sm">No submissions yet</p> : (
                  <HBarChart items={data.submissionsByStage.map(r => ({ name: r.stage, count: Number(r.count) }))} colorMap={{}} />
                )}
              </div>
            </div>
          </Card>

          <Card>
            <SectionTitle icon={ICONS.trendingUp} color="text-[var(--mint)]">Submissions Over Time</SectionTitle>
            <MiniBarChart data={data.submissionsOverTime} valueKey="count" color="var(--mint)" />
          </Card>
        </>
      )}
    </div>
  );
}

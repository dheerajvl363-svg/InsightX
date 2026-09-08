import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { BarChart3, Clock, TrendingUp } from 'lucide-react';
import type { TimelineResponse } from '../../types/api';
import { Skeleton } from '../common';
import { CustomChartTooltip } from '../dashboard/CustomChartTooltip';

interface TimelineDeepChartProps {
  timeline: TimelineResponse | null;
  loading: boolean;
  selectedInterval: 'hour' | 'day' | 'week';
  onIntervalChange: (interval: 'hour' | 'day' | 'week') => void;
  selectedPlatform: string;
  onPlatformChange: (platform: string) => void;
}

const PLATFORMS = [
  { id: 'all', label: 'All Feeds' },
  { id: 'X', label: 'X (Twitter)' },
  { id: 'Reddit', label: 'Reddit' },
  { id: 'Telegram', label: 'Telegram' },
  { id: 'YouTube', label: 'YouTube' },
];

export const TimelineDeepChart: React.FC<TimelineDeepChartProps> = ({
  timeline,
  loading,
  selectedInterval,
  onIntervalChange,
  selectedPlatform,
  onPlatformChange,
}) => {
  if (loading) {
    return (
      <div style={{ height: '340px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton width="100%" height="300px" borderRadius="var(--radius-md)" />
      </div>
    );
  }

  const buckets = timeline?.buckets ?? [];

  if (buckets.length === 0) {
    return (
      <div
        style={{
          height: '320px',
          border: '1px dashed var(--border-muted)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          textAlign: 'center',
        }}
      >
        <BarChart3 size={38} color="var(--text-muted)" style={{ marginBottom: '0.75rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
          No Chronological Data Recorded
        </h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '380px' }}>
          Database has 0 posts matching the selected timeframe and filter criteria.
        </p>
      </div>
    );
  }

  // Transform buckets into Recharts friendly series
  const chartData = buckets.map((bucket) => {
    const d = new Date(bucket.timestamp);
    let label = '';
    if (selectedInterval === 'hour') {
      label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } else {
      label = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }

    const fullDate = d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: selectedInterval === 'hour' ? '2-digit' : undefined,
      minute: selectedInterval === 'hour' ? '2-digit' : undefined,
    });

    const breakdown = bucket.platform_breakdown || {};

    return {
      rawTimestamp: bucket.timestamp,
      displayLabel: label,
      fullDate,
      total: bucket.count,
      x: breakdown['X'] ?? breakdown['x'] ?? 0,
      reddit: breakdown['Reddit'] ?? breakdown['reddit'] ?? 0,
      telegram: breakdown['Telegram'] ?? breakdown['telegram'] ?? 0,
      youtube: breakdown['YouTube'] ?? breakdown['youtube'] ?? 0,
    };
  });

  const peakBucket = buckets.reduce((max, b) => (b.count > max.count ? b : max), buckets[0]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Controls Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        {/* Platform Selector Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, marginRight: '0.2rem' }}>
            Filter:
          </span>
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              onClick={() => onPlatformChange(p.id)}
              style={{
                backgroundColor: selectedPlatform === p.id ? 'var(--accent-cyan-bg)' : 'var(--bg-tertiary)',
                color: selectedPlatform === p.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: `1px solid ${selectedPlatform === p.id ? 'rgba(0, 210, 255, 0.4)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-full)',
                padding: '0.25rem 0.65rem',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Granularity Selector Switcher */}
        <div
          style={{
            display: 'flex',
            gap: '0.2rem',
            backgroundColor: 'var(--bg-tertiary)',
            padding: '0.2rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {(['hour', 'day', 'week'] as const).map((intv) => (
            <button
              key={intv}
              onClick={() => onIntervalChange(intv)}
              style={{
                background: selectedInterval === intv ? 'var(--bg-surface)' : 'transparent',
                color: selectedInterval === intv ? 'var(--accent-cyan)' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-xs)',
                padding: '0.25rem 0.65rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'all var(--transition-fast)',
              }}
            >
              {intv}
            </button>
          ))}
        </div>
      </div>

      {/* Recharts Area Container */}
      <div style={{ width: '100%', height: '280px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="totalVelocityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00d2ff" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="xGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1da1f2" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#1da1f2" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="redditGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff4500" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#ff4500" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="telegramGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#229ed9" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#229ed9" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border-subtle)"
              vertical={false}
              opacity={0.6}
            />

            <XAxis
              dataKey="displayLabel"
              stroke="var(--text-muted)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'var(--border-subtle)' }}
            />

            <YAxis
              stroke="var(--text-muted)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'var(--border-subtle)' }}
              allowDecimals={false}
            />

            <Tooltip
              content={
                <CustomChartTooltip
                  labelFormatter={(_lbl) => ''}
                  formatter={(val, name, item) => {
                    const fullDate = (item.payload?.fullDate as string) || '';
                    return [`${Number(val).toLocaleString()} posts`, name || fullDate];
                  }}
                />
              }
            />

            <Area
              type="monotone"
              dataKey="total"
              name="Total Volume"
              stroke="var(--accent-cyan)"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#totalVelocityGradient)"
              activeDot={{
                r: 5,
                fill: 'var(--accent-cyan)',
                stroke: 'var(--bg-primary)',
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Footer Telemetry */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '0.75rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <TrendingUp size={16} color="var(--accent-cyan)" />
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Total Ingested</span>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              {(timeline?.total_posts ?? 0).toLocaleString()} posts
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Clock size={16} color="var(--accent-purple)" />
          <div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Resolution</span>
            <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
              {timeline?.granularity ?? selectedInterval} ({timeline?.total_buckets ?? buckets.length} buckets)
            </span>
          </div>
        </div>

        {peakBucket && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BarChart3 size={16} color="var(--sentiment-pos)" />
            <div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block' }}>Peak Volume</span>
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--sentiment-pos)', fontFamily: 'var(--font-mono)' }}>
                {peakBucket.count} posts ({new Date(peakBucket.timestamp).toLocaleDateString()})
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

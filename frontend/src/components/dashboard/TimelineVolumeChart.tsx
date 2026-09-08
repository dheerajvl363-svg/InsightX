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
import { BarChart3 } from 'lucide-react';
import type { TimelineResponse } from '../../types/api';
import { Skeleton } from '../common';
import { CustomChartTooltip } from './CustomChartTooltip';

interface TimelineVolumeChartProps {
  timeline: TimelineResponse | null;
  loading: boolean;
  selectedInterval: 'hour' | 'day' | 'week';
  onIntervalChange: (interval: 'hour' | 'day' | 'week') => void;
}

export const TimelineVolumeChart: React.FC<TimelineVolumeChartProps> = ({
  timeline,
  loading,
  selectedInterval,
  onIntervalChange,
}) => {
  if (loading) {
    return (
      <div style={{ height: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton width="100%" height="250px" borderRadius="var(--radius-md)" />
      </div>
    );
  }

  const buckets = timeline?.buckets ?? [];

  if (buckets.length === 0) {
    return (
      <div
        style={{
          height: '280px',
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
        <BarChart3 size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
          No Timeline Activity Recorded
        </h4>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', maxWidth: '380px' }}>
          Database currently has 0 posts matching the selected timeframe. Load social posts to populate activity streams.
        </p>
      </div>
    );
  }

  // Transform backend buckets into Recharts friendly series
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

    return {
      rawTimestamp: bucket.timestamp,
      displayLabel: label,
      fullDate,
      count: bucket.count,
      ...(bucket.platform_breakdown || {}),
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Interval Selector Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
        }}
      >
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Total posts: <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{timeline?.total_posts ?? 0}</span> across{' '}
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{timeline?.total_buckets ?? buckets.length}</span> interval buckets
        </div>

        <div
          style={{
            display: 'flex',
            gap: '0.25rem',
            backgroundColor: 'var(--bg-tertiary)',
            padding: '0.2rem',
            borderRadius: 'var(--radius-sm)',
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

      {/* Responsive Recharts Area Container */}
      <div style={{ width: '100%', height: '240px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 12, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="volumeCyanGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00d2ff" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
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
                  formatter={(val, _name, item) => {
                    const fullDate = (item.payload?.fullDate as string) || '';
                    return [`${Number(val).toLocaleString()} posts`, fullDate || 'Volume'];
                  }}
                />
              }
            />

            <Area
              type="monotone"
              dataKey="count"
              name="Post Velocity"
              stroke="var(--accent-cyan)"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#volumeCyanGradient)"
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
    </div>
  );
};

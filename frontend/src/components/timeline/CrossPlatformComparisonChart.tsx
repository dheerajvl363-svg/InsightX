import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';
import { Layers } from 'lucide-react';
import type { PlatformSummary } from '../../types/api';
import { Skeleton, Badge } from '../common';
import { CustomChartTooltip } from '../dashboard/CustomChartTooltip';

interface CrossPlatformComparisonChartProps {
  platforms: PlatformSummary[];
  loading: boolean;
}

const PLATFORM_COLORS: Record<string, string> = {
  x: '#1da1f2',
  reddit: '#ff4500',
  telegram: '#229ed9',
  youtube: '#ff0000',
};

const getPlatformColor = (platform: string) => {
  return PLATFORM_COLORS[platform.toLowerCase()] || '#8b5cf6';
};

const getBadgeVariant = (platform: string) => {
  const key = platform.toLowerCase();
  if (key === 'x') return 'x' as const;
  if (key === 'reddit') return 'reddit' as const;
  if (key === 'telegram') return 'telegram' as const;
  if (key === 'youtube') return 'youtube' as const;
  return 'cyan' as const;
};

export const CrossPlatformComparisonChart: React.FC<CrossPlatformComparisonChartProps> = ({
  platforms,
  loading,
}) => {
  if (loading) {
    return (
      <div style={{ height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton width="100%" height="200px" borderRadius="var(--radius-md)" />
      </div>
    );
  }

  if (!platforms || platforms.length === 0) {
    return (
      <div
        style={{
          height: '200px',
          border: '1px dashed var(--border-muted)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          textAlign: 'center',
        }}
      >
        <Layers size={32} color="var(--text-muted)" style={{ marginBottom: '0.5rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
          No Platform Comparison Data
        </h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '300px' }}>
          Ingest multi-network feeds to enable comparative stream analytics.
        </p>
      </div>
    );
  }

  const totalPosts = platforms.reduce((acc, p) => acc + p.post_count, 0);

  const chartData = platforms.map((p) => {
    const percentage = p.percentage !== undefined ? p.percentage : totalPosts > 0 ? Math.round((p.post_count / totalPosts) * 100) : 0;
    return {
      name: p.platform,
      posts: p.post_count,
      percentage,
      color: getPlatformColor(p.platform),
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ width: '100%', height: '180px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} opacity={0.6} />
            <XAxis
              dataKey="name"
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
                  formatter={(val, name, item) => {
                    const pct = (item.payload?.percentage as number) || 0;
                    return [`${Number(val).toLocaleString()} posts (${pct}%)`, name || 'Volume'];
                  }}
                />
              }
            />
            <Bar dataKey="posts" name="Ingested Posts" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Platform Chips Row */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.65rem', justifyContent: 'center' }}>
        {chartData.map((p) => (
          <div
            key={p.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.35rem 0.65rem',
              backgroundColor: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
            }}
          >
            <Badge variant={getBadgeVariant(p.name)} size="sm">
              {p.name}
            </Badge>
            <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
              {p.posts.toLocaleString()} ({p.percentage}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

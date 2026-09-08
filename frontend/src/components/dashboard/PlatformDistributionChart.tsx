import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { PieChart as PieChartIcon } from 'lucide-react';
import type { PlatformSummary } from '../../types/api';
import { Badge, Skeleton } from '../common';
import { CustomChartTooltip } from './CustomChartTooltip';

interface PlatformDistributionChartProps {
  platforms: PlatformSummary[];
  totalPosts: number;
  loading: boolean;
}

const PLATFORM_COLORS: Record<string, string> = {
  x: '#1da1f2',
  reddit: '#ff4500',
  telegram: '#229ed9',
  youtube: '#ff0000',
};

const getPlatformColor = (platformName: string): string => {
  const key = platformName.toLowerCase();
  return PLATFORM_COLORS[key] || '#8b5cf6';
};

const getBadgeVariant = (platformName: string): 'x' | 'reddit' | 'telegram' | 'youtube' | 'cyan' => {
  const key = platformName.toLowerCase();
  if (key === 'x') return 'x';
  if (key === 'reddit') return 'reddit';
  if (key === 'telegram') return 'telegram';
  if (key === 'youtube') return 'youtube';
  return 'cyan';
};

export const PlatformDistributionChart: React.FC<PlatformDistributionChartProps> = ({
  platforms,
  totalPosts,
  loading,
}) => {
  if (loading) {
    return (
      <div style={{ height: '280px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton width="100%" height="250px" borderRadius="var(--radius-md)" />
      </div>
    );
  }

  if (platforms.length === 0) {
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
        <PieChartIcon size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
          No Platform Data Available
        </h4>
        <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', maxWidth: '320px' }}>
          Ingest data through the ingestion pipeline to populate network share metrics.
        </p>
      </div>
    );
  }

  const effectiveTotal = Math.max(
    totalPosts,
    platforms.reduce((acc, p) => acc + p.post_count, 0),
    1
  );

  const chartData = platforms.map((p) => {
    const pct = p.percentage !== undefined ? p.percentage : Math.round((p.post_count / effectiveTotal) * 100);
    return {
      name: p.platform,
      value: p.post_count,
      percentage: pct,
      color: getPlatformColor(p.platform),
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Donut Chart Container */}
        <div style={{ width: '160px', height: '160px', position: 'relative', margin: '0 auto' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={48}
                outerRadius={70}
                paddingAngle={3}
                stroke="none"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                content={
                  <CustomChartTooltip
                    formatter={(val, name, item) => {
                      const pct = (item.payload?.percentage as number) || 0;
                      return [`${Number(val).toLocaleString()} posts (${pct}%)`, name];
                    }}
                  />
                }
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Donut Center Display */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              pointerEvents: 'none',
            }}
          >
            <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              {platforms.length}
            </span>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Networks
            </span>
          </div>
        </div>

        {/* Legend / Platform Bar List */}
        <div style={{ flex: 1, minWidth: '180px', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {chartData.map((item) => (
            <div key={item.name}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '0.25rem',
                  fontSize: '0.8rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Badge variant={getBadgeVariant(item.name)} size="sm">
                    {item.name}
                  </Badge>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {item.value.toLocaleString()} posts
                  </span>
                </div>
                <span
                  style={{
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {item.percentage}%
                </span>
              </div>

              {/* Share Progress Bar */}
              <div
                style={{
                  height: '6px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${Math.min(item.percentage, 100)}%`,
                    height: '100%',
                    backgroundColor: item.color,
                    borderRadius: 'var(--radius-full)',
                    transition: 'width var(--transition-normal)',
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  Tooltip,
} from 'recharts';
import { Smile } from 'lucide-react';
import type { BatchSentimentResult } from '../../types/api';
import { Badge, Skeleton } from '../common';
import { CustomChartTooltip } from './CustomChartTooltip';

interface SentimentAnalyticsChartProps {
  sentiment: BatchSentimentResult | undefined | null;
  loading: boolean;
}

export const SentimentAnalyticsChart: React.FC<SentimentAnalyticsChartProps> = ({
  sentiment,
  loading,
}) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', justifyContent: 'center' }}>
        <Skeleton height="1.5rem" />
        <Skeleton height="4rem" />
        <Skeleton height="3rem" />
      </div>
    );
  }

  const positiveCount = sentiment?.positive_count ?? 0;
  const neutralCount = sentiment?.neutral_count ?? 0;
  const negativeCount = sentiment?.negative_count ?? 0;
  const totalAnalyzed = sentiment?.total_analyzed ?? (positiveCount + neutralCount + negativeCount);
  const avgScore = sentiment?.average_score ?? 0;

  if (totalAnalyzed === 0) {
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
        <Smile size={32} color="var(--text-muted)" style={{ marginBottom: '0.5rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
          No Sentiment Signals Analyzed
        </h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '280px' }}>
          Run sentiment analysis on ingested posts to calculate net polarity scores.
        </p>
      </div>
    );
  }

  const posPct = Math.round((positiveCount / totalAnalyzed) * 100);
  const neuPct = Math.round((neutralCount / totalAnalyzed) * 100);
  const negPct = Math.round((negativeCount / totalAnalyzed) * 100);

  const chartData = [
    {
      category: 'Positive',
      count: positiveCount,
      percentage: posPct,
      color: '#00e676',
    },
    {
      category: 'Neutral',
      count: neutralCount,
      percentage: neuPct,
      color: '#ffb142',
    },
    {
      category: 'Negative',
      count: negativeCount,
      percentage: negPct,
      color: '#ff5252',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      {/* Top Polarity Summary Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.75rem 1rem',
          backgroundColor: 'var(--bg-tertiary)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Net Sentiment Score
          </span>
          <span
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              color: avgScore >= 0.05 ? 'var(--sentiment-pos)' : avgScore <= -0.05 ? 'var(--sentiment-neg)' : 'var(--sentiment-neu)',
            }}
          >
            {avgScore >= 0 ? '+' : ''}{avgScore.toFixed(2)} NSS
          </span>
        </div>

        <Badge
          variant={avgScore >= 0.05 ? 'positive' : avgScore <= -0.05 ? 'negative' : 'neutral'}
          size="md"
        >
          {avgScore >= 0.05 ? 'Bullish Polarity' : avgScore <= -0.05 ? 'Bearish Polarity' : 'Neutral Polarity'}
        </Badge>
      </div>

      {/* Recharts Horizontal Distribution Chart */}
      <div style={{ width: '100%', height: '110px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 30, left: 10, bottom: 0 }}
          >
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="category"
              stroke="var(--text-secondary)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              width={70}
            />
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
            <Bar dataKey="count" name="Posts" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Itemized Percentage Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', textAlign: 'center' }}>
        <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(0, 230, 118, 0.08)' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--sentiment-pos)', fontWeight: 600, display: 'block' }}>Positive</span>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {posPct}%
          </span>
        </div>

        <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(255, 177, 66, 0.08)' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--sentiment-neu)', fontWeight: 600, display: 'block' }}>Neutral</span>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {neuPct}%
          </span>
        </div>

        <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'rgba(255, 82, 82, 0.08)' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--sentiment-neg)', fontWeight: 600, display: 'block' }}>Negative</span>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {negPct}%
          </span>
        </div>
      </div>
    </div>
  );
};

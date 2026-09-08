import React, { useState } from 'react';
import {
  TrendingUp,
  Flame,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Layers,
  Search,
} from 'lucide-react';
import type { BatchTrendResult, TopicTrendResult } from '../../types/api';
import { Card, Badge, Skeleton } from '../common';

interface TrendRadarSectionProps {
  trendsData: BatchTrendResult | null;
  loading: boolean;
  onSelectTrend: (trend: TopicTrendResult) => void;
}

export const TrendRadarSection: React.FC<TrendRadarSectionProps> = ({
  trendsData,
  loading,
  onSelectTrend,
}) => {
  const [directionFilter, setDirectionFilter] = useState<string>('all');
  const [searchFilter, setSearchFilter] = useState<string>('');

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <Skeleton height="80px" />
          <Skeleton height="80px" />
          <Skeleton height="80px" />
          <Skeleton height="80px" />
        </div>
        <Skeleton height="240px" />
      </div>
    );
  }

  const trends = trendsData?.trends ?? [];
  const emergingCount = trendsData?.emerging_topics_count ?? 0;
  const spikingCount = trendsData?.spiking_topics_count ?? 0;
  const growingCount = trendsData?.growing_topics_count ?? 0;
  const totalEvaluated = trendsData?.total_topics_evaluated ?? trends.length;

  const filteredTrends = trends.filter((t) => {
    if (directionFilter !== 'all' && t.direction.toLowerCase() !== directionFilter) {
      return false;
    }
    if (searchFilter.trim() && !t.topic_label.toLowerCase().includes(searchFilter.toLowerCase().trim())) {
      return false;
    }
    return true;
  });

  const getDirectionBadge = (direction: string) => {
    switch (direction.toLowerCase()) {
      case 'spiking':
        return { variant: 'negative' as const, label: 'Spiking', icon: Flame };
      case 'emerging':
        return { variant: 'cyan' as const, label: 'Emerging', icon: Sparkles };
      case 'growing':
        return { variant: 'positive' as const, label: 'Growing', icon: ArrowUpRight };
      case 'declining':
        return { variant: 'neutral' as const, label: 'Declining', icon: ArrowDownRight };
      default:
        return { variant: 'neutral' as const, label: 'Stable', icon: Minus };
    }
  };

  const directionTabs = [
    { id: 'all', label: `All (${trends.length})` },
    { id: 'emerging', label: `Emerging (${emergingCount})` },
    { id: 'spiking', label: `Spiking (${spikingCount})` },
    { id: 'growing', label: `Growing (${growingCount})` },
    { id: 'stable', label: 'Stable' },
    { id: 'declining', label: 'Declining' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Trend Summary Metric Badges */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}
      >
        <Card style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-purple-bg)', color: 'var(--accent-purple)' }}>
              <Layers size={18} />
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Evaluated Clusters</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {totalEvaluated}
              </div>
            </div>
          </div>
        </Card>

        <Card style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-cyan-bg)', color: 'var(--accent-cyan)' }}>
              <Sparkles size={18} />
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Emerging Signals</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>
                {emergingCount}
              </div>
            </div>
          </div>
        </Card>

        <Card style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--sentiment-neg-bg)', color: 'var(--sentiment-neg)' }}>
              <Flame size={18} />
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Spiking Anomalies</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--sentiment-neg)', fontFamily: 'var(--font-mono)' }}>
                {spikingCount}
              </div>
            </div>
          </div>
        </Card>

        <Card style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--sentiment-pos-bg)', color: 'var(--sentiment-pos)' }}>
              <ArrowUpRight size={18} />
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Growing Trajectories</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--sentiment-pos)', fontFamily: 'var(--font-mono)' }}>
                {growingCount}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        {/* Direction Filter Tabs */}
        <div
          style={{
            display: 'flex',
            gap: '0.35rem',
            backgroundColor: 'var(--bg-tertiary)',
            padding: '0.25rem',
            borderRadius: 'var(--radius-md)',
            flexWrap: 'wrap',
          }}
        >
          {directionTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setDirectionFilter(tab.id)}
              style={{
                background: directionFilter === tab.id ? 'var(--bg-surface)' : 'transparent',
                color: directionFilter === tab.id ? 'var(--accent-cyan)' : 'var(--text-muted)',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                padding: '0.35rem 0.75rem',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input in Topics */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.4rem 0.75rem',
            minWidth: '220px',
          }}
        >
          <Search size={14} color="var(--text-muted)" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Filter trends by keyword..."
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              outline: 'none',
              fontSize: '0.825rem',
              width: '100%',
            }}
          />
        </div>
      </div>

      {/* Trend Cards Grid */}
      {filteredTrends.length === 0 ? (
        <div
          style={{
            padding: '3rem 2rem',
            textAlign: 'center',
            backgroundColor: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-muted)',
          }}
        >
          <TrendingUp size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem', opacity: 0.6 }} />
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.3rem' }}>
            No Trend Trajectories Recorded
          </h4>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', maxWidth: '340px', margin: '0 auto' }}>
            No topic trends matched the active direction filter. Ingest additional multi-period posts to evaluate velocity.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {filteredTrends.map((trend, idx) => {
            const badgeInfo = getDirectionBadge(trend.direction);
            const DirIcon = badgeInfo.icon;

            return (
              <Card
                key={trend.topic_id || idx}
                onClick={() => onSelectTrend(trend)}
                style={{
                  cursor: 'pointer',
                  transition: 'transform var(--transition-fast), border-color var(--transition-fast)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
                headerAction={
                  <Badge variant={badgeInfo.variant} size="sm">
                    <DirIcon size={12} style={{ marginRight: '0.25rem', display: 'inline' }} />
                    {badgeInfo.label}
                  </Badge>
                }
                footer={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    <span>Rank: #{idx + 1}</span>
                    <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                      Inspect Telemetry &rarr;
                    </span>
                  </div>
                }
              >
                <div>
                  <h4
                    style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      marginBottom: '0.75rem',
                    }}
                  >
                    {trend.topic_label}
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <div style={{ padding: '0.5rem 0.65rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Growth Rate</span>
                      <span
                        style={{
                          fontSize: '0.95rem',
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          color: trend.growth_rate > 0 ? 'var(--sentiment-pos)' : trend.growth_rate < 0 ? 'var(--sentiment-neg)' : 'var(--text-primary)',
                        }}
                      >
                        {trend.growth_rate >= 0 ? '+' : ''}{trend.growth_rate.toFixed(1)}%
                      </span>
                    </div>

                    <div style={{ padding: '0.5rem 0.65rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block' }}>Trend Score</span>
                      <span style={{ fontSize: '0.95rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                        {trend.trend_score.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Current Window: <strong style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{trend.current_volume}</strong> posts
                    {' '}(Baseline: <strong style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{trend.baseline_volume}</strong>)
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

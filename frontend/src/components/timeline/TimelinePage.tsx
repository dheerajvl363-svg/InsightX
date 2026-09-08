import React, { useState } from 'react';
import {
  RefreshCw,
  Sliders,
} from 'lucide-react';
import { Card, Badge, Button, ErrorBanner } from '../common';
import { useTimeline } from '../../hooks/useTimeline';
import { useTrends } from '../../hooks/useTrends';
import { useOverview } from '../../hooks/useOverview';
import type { TopicTrendResult } from '../../types/api';
import { TimelineDeepChart } from './TimelineDeepChart';
import { TrendRadarSection } from './TrendRadarSection';
import { TrendDetailModal } from './TrendDetailModal';
import { CrossPlatformComparisonChart } from './CrossPlatformComparisonChart';

export const TimelinePage: React.FC = () => {
  const [selectedInterval, setSelectedInterval] = useState<'hour' | 'day' | 'week'>('day');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [selectedTrend, setSelectedTrend] = useState<TopicTrendResult | null>(null);

  // Real backend API hooks
  const platformParam = selectedPlatform !== 'all' ? selectedPlatform : undefined;
  const {
    data: timeline,
    loading: timelineLoading,
    error: timelineError,
    refetch: refetchTimeline,
  } = useTimeline(selectedInterval, platformParam);

  const {
    data: trendsData,
    loading: trendsLoading,
    error: trendsError,
    refetch: refetchTrends,
  } = useTrends(platformParam ? { platform: platformParam } : {});

  const {
    data: overview,
    loading: overviewLoading,
    refetch: refetchOverview,
  } = useOverview();

  const handleRefreshAll = async () => {
    await Promise.all([refetchTimeline(), refetchTrends(), refetchOverview()]);
  };

  const platforms = overview?.platforms ?? [];

  return (
    <div className="page-container">
      {/* Header */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '2rem',
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              marginBottom: '0.35rem',
            }}
          >
            Chronological Timeline & Trend Intelligence
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
            Multi-interval volume velocity, statistical trend trajectories, and emerging narrative signals.
          </p>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={14} className={timelineLoading || trendsLoading ? 'animate-spin' : ''} />}
            onClick={handleRefreshAll}
            disabled={timelineLoading || trendsLoading}
          >
            Sync Temporal Data
          </Button>

          <Badge variant={timelineError || trendsError ? 'negative' : 'cyan'} size="md">
            {timelineError || trendsError ? 'Sync Notice' : 'Live /timeline'}
          </Badge>
        </div>
      </div>

      {/* Error Banners if any endpoint encounters an error */}
      {timelineError && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorBanner
            title="Timeline Telemetry Notice"
            message={timelineError}
            onRetry={refetchTimeline}
          />
        </div>
      )}
      {trendsError && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorBanner
            title="Trend Momentum Analytics Notice"
            message={trendsError}
            onRetry={refetchTrends}
          />
        </div>
      )}

      {/* Primary Visual: Deep Volume Timeline */}
      <Card
        title="Multi-Platform Chronological Volume & Ingestion Velocity"
        subtitle={`Resolution: ${selectedInterval.toUpperCase()} — Live backend aggregation window`}
        style={{ marginBottom: '2rem' }}
      >
        <TimelineDeepChart
          timeline={timeline}
          loading={timelineLoading}
          selectedInterval={selectedInterval}
          onIntervalChange={setSelectedInterval}
          selectedPlatform={selectedPlatform}
          onPlatformChange={setSelectedPlatform}
        />
      </Card>

      {/* Lower Row: Trend Detection Radar & Cross-Platform Comparison */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        {/* Trend Radar & Narrative Clusters */}
        <div style={{ gridColumn: '1 / -1' }}>
          <Card
            title="Emergent Narrative Radar & Velocity Classifications"
            subtitle={`Classified topics: ${trendsData?.total_topics_evaluated ?? 0} — Model: ${trendsData?.model || 'TrendEngine-v1'}`}
            headerAction={
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                <Sliders size={14} color="var(--accent-cyan)" />
                <span>Ranked by Trend Score</span>
              </div>
            }
          >
            <TrendRadarSection
              trendsData={trendsData}
              loading={trendsLoading}
              onSelectTrend={setSelectedTrend}
            />
          </Card>
        </div>

        {/* Cross-Platform Comparative Distribution */}
        <div style={{ gridColumn: '1 / -1' }}>
          <Card
            title="Cross-Network Comparative Stream Ingestion"
            subtitle={`Ingestion across ${platforms.length} connected feeds`}
            footer={
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>Endpoint: GET /api/v1/analytics/overview</span>
                <span style={{ color: 'var(--accent-cyan)' }}>Normalized Ingestion Shares</span>
              </div>
            }
          >
            <CrossPlatformComparisonChart
              platforms={platforms}
              loading={overviewLoading}
            />
          </Card>
        </div>
      </div>

      {/* Trend Detail Statistical Modal */}
      <TrendDetailModal
        trend={selectedTrend}
        onClose={() => setSelectedTrend(null)}
      />
    </div>
  );
};

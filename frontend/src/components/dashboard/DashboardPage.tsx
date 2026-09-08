import React, { useState } from 'react';
import {
  Database,
  TrendingUp,
  Sparkles,
  Layers,
  RefreshCw,
} from 'lucide-react';
import { Card, StatCard, Badge, Button, ErrorBanner } from '../common';
import { useOverview } from '../../hooks/useOverview';
import { useTimeline } from '../../hooks/useTimeline';
import { TimelineVolumeChart } from './TimelineVolumeChart';
import { PlatformDistributionChart } from './PlatformDistributionChart';
import { SentimentAnalyticsChart } from './SentimentAnalyticsChart';
import { TopicEmergenceChart } from './TopicEmergenceChart';

export const DashboardPage: React.FC = () => {
  const [selectedInterval, setSelectedInterval] = useState<'hour' | 'day' | 'week'>('day');

  // Real backend API hooks
  const {
    data: overview,
    loading: overviewLoading,
    error: overviewError,
    refetch: refetchOverview,
  } = useOverview();

  const {
    data: timeline,
    loading: timelineLoading,
    error: timelineError,
    refetch: refetchTimeline,
  } = useTimeline(selectedInterval);

  const handleRefreshAll = async () => {
    await Promise.all([refetchOverview(), refetchTimeline()]);
  };

  // Derived metrics from real overview payload
  const totalPosts = overview?.total_posts ?? 0;
  const sentiment = overview?.sentiment;
  const topics = overview?.topics?.topics ?? [];
  const platforms = overview?.platforms ?? [];
  const avgScore = sentiment?.average_score ?? 0;
  const positiveCount = sentiment?.positive_count ?? 0;
  const negativeCount = sentiment?.negative_count ?? 0;
  const topTopicLabel = topics[0]?.label || 'Keyword NLP analysis';

  return (
    <div className="page-container">
      {/* View Header with Controls */}
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
            Executive Intelligence Command Center
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
            Live multi-platform social stream intelligence synthesized from FastAPI backend endpoints.
          </p>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={14} className={overviewLoading || timelineLoading ? 'animate-spin' : ''} />}
            onClick={handleRefreshAll}
            disabled={overviewLoading || timelineLoading}
          >
            Sync Live Data
          </Button>

          <Badge variant={overviewError ? 'negative' : 'cyan'} size="md">
            {overviewError ? 'Sync Error' : 'Live /api/v1'}
          </Badge>
        </div>
      </div>

      {/* Error Banners if any endpoint fails */}
      {overviewError && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorBanner
            title="Overview Analytics Failed"
            message={overviewError}
            onRetry={refetchOverview}
          />
        </div>
      )}
      {timelineError && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorBanner
            title="Timeline Query Notice"
            message={timelineError}
            onRetry={refetchTimeline}
          />
        </div>
      )}

      {/* KPI Stat Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '1.25rem',
          marginBottom: '2rem',
        }}
      >
        <StatCard
          label="Total Posts Ingested"
          value={overviewLoading ? '...' : totalPosts.toLocaleString()}
          loading={overviewLoading}
          icon={<Database size={20} />}
          iconBg="rgba(0, 210, 255, 0.12)"
          iconColor="var(--accent-cyan)"
          subtext={`Evaluated across ${platforms.length} platform(s)`}
          badge={<Badge variant="cyan" size="sm">GET /posts</Badge>}
        />

        <StatCard
          label="Net Sentiment Polarity"
          value={
            overviewLoading
              ? '...'
              : `${avgScore >= 0 ? '+' : ''}${avgScore.toFixed(2)} NSS`
          }
          loading={overviewLoading}
          icon={<TrendingUp size={20} />}
          iconBg={avgScore >= 0.05 ? 'rgba(0, 230, 118, 0.12)' : avgScore <= -0.05 ? 'rgba(255, 82, 82, 0.12)' : 'rgba(255, 177, 66, 0.12)'}
          iconColor={avgScore >= 0.05 ? 'var(--sentiment-pos)' : avgScore <= -0.05 ? 'var(--sentiment-neg)' : 'var(--sentiment-neu)'}
          subtext={`${positiveCount} Pos / ${negativeCount} Neg`}
          badge={
            <Badge variant={avgScore >= 0.05 ? 'positive' : avgScore <= -0.05 ? 'negative' : 'neutral'} size="sm">
              {avgScore >= 0.05 ? 'Positive' : avgScore <= -0.05 ? 'Negative' : 'Neutral'}
            </Badge>
          }
        />

        <StatCard
          label="Extracted Topic Clusters"
          value={overviewLoading ? '...' : `${overview?.topics?.total_topics_found ?? 0} Clusters`}
          loading={overviewLoading}
          icon={<Sparkles size={20} />}
          iconBg="rgba(139, 92, 246, 0.12)"
          iconColor="var(--accent-purple)"
          subtext={topics[0] ? `Top: ${topTopicLabel}` : 'Keyword NLP analysis'}
          badge={<Badge variant="primary" size="sm">Phase 3.4</Badge>}
        />

        <StatCard
          label="Platform Breakdown"
          value={overviewLoading ? '...' : `${platforms.length} Feeds`}
          loading={overviewLoading}
          icon={<Layers size={20} />}
          iconBg="rgba(255, 177, 66, 0.12)"
          iconColor="var(--sentiment-neu)"
          subtext={platforms.map((p) => p.platform).join(', ') || 'X, Reddit, TG, YT'}
          badge={<Badge variant="neutral" size="sm">Normalized</Badge>}
        />
      </div>

      {/* Main Visualizations Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}
      >
        {/* Timeline Volume Velocity Card */}
        <Card
          title="Chronological Post Activity & Volume Velocity"
          subtitle={`Granularity: ${selectedInterval.toUpperCase()} — Live stream telemetry`}
          style={{ minHeight: '380px' }}
        >
          <TimelineVolumeChart
            timeline={timeline}
            loading={timelineLoading}
            selectedInterval={selectedInterval}
            onIntervalChange={setSelectedInterval}
          />
        </Card>

        {/* Platform Share Distribution Card */}
        <Card
          title="Platform Ingestion Distribution"
          subtitle={`Connected networks: ${platforms.length}`}
          style={{ minHeight: '380px' }}
        >
          <PlatformDistributionChart
            platforms={platforms}
            totalPosts={totalPosts}
            loading={overviewLoading}
          />
        </Card>
      </div>

      {/* Lower Row Intelligence Visualizations */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '1.5rem',
        }}
      >
        {/* Sentiment Polarity Breakdown Card */}
        <Card
          title="Net Sentiment & Polarity Index"
          subtitle={`Evaluated posts: ${sentiment?.total_analyzed ?? 0}`}
          footer={
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Endpoint: GET /api/v1/analytics/sentiment</span>
              <span style={{ color: avgScore >= 0.05 ? 'var(--sentiment-pos)' : avgScore <= -0.05 ? 'var(--sentiment-neg)' : 'var(--sentiment-neu)', fontWeight: 600 }}>
                Average: {avgScore.toFixed(2)}
              </span>
            </div>
          }
        >
          <SentimentAnalyticsChart
            sentiment={sentiment}
            loading={overviewLoading}
          />
        </Card>

        {/* Top Thematic Topics & Emergent Narratives Card */}
        <Card
          title="Top Thematic Topics & Emergent Narratives"
          subtitle={`Identified clusters: ${topics.length}`}
          footer={
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Endpoint: GET /api/v1/analytics/topics</span>
              <span style={{ color: 'var(--accent-cyan)' }}>Ranked by Post Count</span>
            </div>
          }
        >
          <TopicEmergenceChart
            topics={topics}
            loading={overviewLoading}
          />
        </Card>
      </div>
    </div>
  );
};

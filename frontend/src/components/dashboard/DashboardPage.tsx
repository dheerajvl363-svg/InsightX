import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Database,
  TrendingUp,
  Sparkles,
  Layers,
  RefreshCw,
  ArrowRight,
  Share2,
  Activity,
  Compass,
} from 'lucide-react';
import { Card, StatCard, Badge, Button, ErrorBanner } from '../common';
import { useOverview } from '../../hooks/useOverview';
import { useTimeline } from '../../hooks/useTimeline';
import { useInsights } from '../../hooks/useInsights';
import type { InsightItem } from '../../types/api';
import { TimelineVolumeChart } from './TimelineVolumeChart';
import { PlatformDistributionChart } from './PlatformDistributionChart';
import { SentimentAnalyticsChart } from './SentimentAnalyticsChart';
import { TopicEmergenceChart } from './TopicEmergenceChart';
import { IntelligenceFeedCard } from './IntelligenceFeedCard';
import { InsightExplanationDrawer } from './InsightExplanationDrawer';

const PLATFORMS = [
  { id: 'all', label: 'All Feeds' },
  { id: 'X', label: 'X (Twitter)' },
  { id: 'Reddit', label: 'Reddit' },
  { id: 'Telegram', label: 'Telegram' },
  { id: 'YouTube', label: 'YouTube' },
];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [selectedInterval, setSelectedInterval] = useState<'hour' | 'day' | 'week'>('day');
  const [selectedPlatform, setSelectedPlatform] = useState<string>('all');
  const [selectedInsight, setSelectedInsight] = useState<InsightItem | null>(null);

  const overviewParams = useMemo(() => {
    return selectedPlatform !== 'all' ? { platform: selectedPlatform } : {};
  }, [selectedPlatform]);

  const platformParam = selectedPlatform !== 'all' ? selectedPlatform : undefined;

  // Real backend API hooks
  const {
    data: overview,
    loading: overviewLoading,
    error: overviewError,
    refetch: refetchOverview,
  } = useOverview(overviewParams);

  const {
    data: timeline,
    loading: timelineLoading,
    error: timelineError,
    refetch: refetchTimeline,
  } = useTimeline(selectedInterval, platformParam);

  const {
    data: insightsData,
    loading: insightsLoading,
    error: insightsError,
    refetch: refetchInsights,
  } = useInsights(overviewParams);

  const handleRefreshAll = async () => {
    await Promise.all([refetchOverview(), refetchTimeline(), refetchInsights()]);
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
      {/* View Header with Global Context Controls */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.35rem' }}>
            <h1
              style={{
                fontSize: '1.75rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em',
              }}
            >
              Executive Intelligence Command Center
            </h1>
            <Badge variant="cyan" size="sm">SIH PS 26152</Badge>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
            Live multi-platform stream synthesis, engagement velocity, and emergent narrative tracking.
          </p>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={14} className={overviewLoading || timelineLoading || insightsLoading ? 'animate-spin' : ''} />}
            onClick={handleRefreshAll}
            disabled={overviewLoading || timelineLoading || insightsLoading}
          >
            Sync Live Data
          </Button>

          <Badge variant={overviewError ? 'negative' : 'cyan'} size="md">
            {overviewError ? 'Sync Error' : 'Live /api/v1'}
          </Badge>
        </div>
      </div>

      {/* Global Platform Context Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.75rem',
          padding: '0.75rem 1rem',
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          marginBottom: '1.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Active Stream Filter:
          </span>
          <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedPlatform(p.id)}
                style={{
                  backgroundColor: selectedPlatform === p.id ? 'var(--accent-cyan-bg)' : 'var(--bg-tertiary)',
                  color: selectedPlatform === p.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  border: `1px solid ${selectedPlatform === p.id ? 'rgba(0, 210, 255, 0.4)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-full)',
                  padding: '0.25rem 0.75rem',
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
        </div>

        {/* Quick Intel Navigator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Quick Jump:</span>
          <button
            onClick={() => navigate(selectedPlatform !== 'all' ? `/posts?platform=${selectedPlatform}` : '/posts')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-cyan)',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
            }}
          >
            Posts <ArrowRight size={12} />
          </button>
          <span style={{ color: 'var(--border-muted)' }}>•</span>
          <button
            onClick={() => navigate(selectedPlatform !== 'all' ? `/timeline?platform=${selectedPlatform}` : '/timeline')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--accent-purple)',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
            }}
          >
            Timeline & Trends <ArrowRight size={12} />
          </button>
          <span style={{ color: 'var(--border-muted)' }}>•</span>
          <button
            onClick={() => navigate('/network')}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--sentiment-pos)',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.2rem',
            }}
          >
            Network <ArrowRight size={12} />
          </button>
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

      {/* KPI Stat Cards Grid with Deep Navigation Affordances */}
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
          subtext={`Click to inspect evidence in Posts Explorer`}
          badge={<Badge variant="cyan" size="sm">Explore &rarr;</Badge>}
          onClick={() => navigate(selectedPlatform !== 'all' ? `/posts?platform=${selectedPlatform}` : '/posts')}
          style={{ cursor: 'pointer', transition: 'transform var(--transition-fast)' }}
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
          badge={<Badge variant="primary" size="sm">Trends &rarr;</Badge>}
          onClick={() => navigate('/timeline')}
          style={{ cursor: 'pointer', transition: 'transform var(--transition-fast)' }}
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

      {/* Synthesized AI Intelligence & Alert Feed */}
      <IntelligenceFeedCard
        insightsData={insightsData}
        loading={insightsLoading}
        error={insightsError}
        onRefresh={refetchInsights}
        onSelectInsight={(insight) => setSelectedInsight(insight)}
        selectedPlatform={platformParam}
      />

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
          headerAction={
            <button
              onClick={() => navigate(selectedPlatform !== 'all' ? `/timeline?platform=${selectedPlatform}` : '/timeline')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-cyan)',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <span>Dedicated View</span>
              <ArrowRight size={13} />
            </button>
          }
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
          headerAction={
            <button
              onClick={() => navigate('/posts')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--accent-cyan)',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
              }}
            >
              <span>Explore Posts</span>
              <ArrowRight size={13} />
            </button>
          }
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
          marginBottom: '2rem',
        }}
      >
        {/* Sentiment Polarity Breakdown Card */}
        <Card
          title="Net Sentiment & Polarity Index"
          subtitle={`Evaluated posts: ${sentiment?.total_analyzed ?? 0}`}
          footer={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Endpoint: GET /api/v1/analytics/sentiment</span>
              <button
                onClick={() => navigate('/posts')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--accent-cyan)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem',
                }}
              >
                Inspect Posts &rarr;
              </button>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Endpoint: GET /api/v1/analytics/topics</span>
              <button
                onClick={() => navigate('/timeline')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--accent-purple)',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.2rem',
                }}
              >
                View Trends Radar &rarr;
              </button>
            </div>
          }
        >
          <TopicEmergenceChart
            topics={topics}
            loading={overviewLoading}
          />
        </Card>
      </div>

      {/* SIH Story Navigator Footer Card */}
      <Card style={{ padding: '1.25rem 1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{ padding: '0.65rem', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--accent-cyan-bg)', color: 'var(--accent-cyan)' }}>
              <Compass size={22} />
            </div>
            <div>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Intelligence Workflow Navigation
              </h4>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                Follow the analytical trail from Executive Overview &rarr; Evidence Explorer &rarr; Timeline & Trends &rarr; Entity Network.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
            <Button size="sm" variant="secondary" icon={<Share2 size={14} />} onClick={() => navigate('/network')}>
              Entity Network
            </Button>
            <Button size="sm" variant="secondary" icon={<Activity size={14} />} onClick={() => navigate('/health')}>
              System Health
            </Button>
            <Button size="sm" variant="primary" icon={<ArrowRight size={14} />} onClick={() => navigate('/posts')}>
              Explore Posts
            </Button>
          </div>
        </div>
      </Card>

      {/* Deep-dive Explanation Drawer */}
      <InsightExplanationDrawer
        insight={selectedInsight}
        platform={platformParam}
        onClose={() => setSelectedInsight(null)}
      />
    </div>
  );
};

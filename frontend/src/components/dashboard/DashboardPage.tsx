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
  ExternalLink,
} from 'lucide-react';
import { Card, StatCard, Badge, Button, ErrorBanner } from '../common';
import { useOverview } from '../../hooks/useOverview';
import { useTimeline } from '../../hooks/useTimeline';
import { useInsights } from '../../hooks/useInsights';
import type { InsightItem, DemoAnalysisResponse } from '../../types/api';
import { TimelineVolumeChart } from './TimelineVolumeChart';
import { PlatformDistributionChart } from './PlatformDistributionChart';
import { SentimentAnalyticsChart } from './SentimentAnalyticsChart';
import { TopicEmergenceChart } from './TopicEmergenceChart';
import { IntelligenceFeedCard } from './IntelligenceFeedCard';
import { InsightExplanationDrawer } from './InsightExplanationDrawer';
import { AnalyzePostModal } from './AnalyzePostModal';

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
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState<boolean>(false);
  const [demoResult, setDemoResult] = useState<DemoAnalysisResponse | null>(null);

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
            variant="primary"
            icon={<Sparkles size={14} />}
            onClick={() => setIsAnalyzeModalOpen(true)}
            style={{
              backgroundColor: 'var(--accent-purple)',
              borderColor: 'var(--accent-purple)',
            }}
          >
            Analyze Social Posts
          </Button>

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

      {/* Phase 9.6: User-Supplied Posts / Primary Evidence Banner */}
      {demoResult && (
        <div
          style={{
            marginBottom: '1.75rem',
            backgroundColor: 'rgba(24, 19, 45, 0.65)',
            border: '1px solid rgba(168, 85, 247, 0.45)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 8px 32px rgba(168, 85, 247, 0.12)',
            overflow: 'hidden',
          }}
        >
          {/* Banner Header */}
          <div
            style={{
              padding: '1rem 1.25rem',
              backgroundColor: 'rgba(30, 27, 75, 0.7)',
              borderBottom: '1px solid rgba(168, 85, 247, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(168, 85, 247, 0.2)',
                  color: 'var(--accent-purple)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Sparkles size={18} />
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Primary User-Supplied Evidence ({demoResult.user_post_count} Post{demoResult.user_post_count > 1 ? 's' : ''})
                  </span>
                  <Badge variant="primary" size="sm">
                    PROVENANCE: {demoResult.provenance.toUpperCase()}
                  </Badge>
                  <Badge variant="cyan" size="sm">
                    Baseline: {demoResult.context_mode.replace('_', ' ').toUpperCase()} ({demoResult.context_post_count} posts)
                  </Badge>
                  {demoResult.persisted && (
                    <Badge variant="positive" size="sm">
                      Persisted to DB
                    </Badge>
                  )}
                </div>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-tertiary)', margin: '2px 0 0 0' }}>
                  Evaluated against {demoResult.context_mode === 'none' ? 'zero background context' : `${demoResult.context_post_count} baseline posts`} (Total Universe: {demoResult.total_context_size}). Deterministic analytics are the source of truth.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setDemoResult(null)}
                style={{ fontSize: '0.75rem' }}
              >
                Exit Demo Mode
              </Button>
            </div>
          </div>

          {/* Seed Posts Cards Grid */}
          <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Submitted Seed Post{demoResult.seed_posts.length > 1 ? 's' : ''}:
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: demoResult.seed_posts.length > 1 ? 'repeat(auto-fit, minmax(300px, 1fr))' : '1fr',
                gap: '0.85rem',
              }}
            >
              {demoResult.seed_posts.map((post, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.9rem 1rem',
                    backgroundColor: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <Badge variant="cyan" size="sm">{post.platform}</Badge>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {post.author_username || post.author_display_name || 'Anonymous'}
                      </span>
                    </div>
                    {post.url && (
                      <a
                        href={post.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '2px', fontSize: '0.72rem' }}
                      >
                        <span>View Post</span>
                        <ExternalLink size={11} />
                      </a>
                    )}
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.45, margin: 0 }}>
                    {post.text}
                  </p>

                  {/* Metrics pills */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', fontSize: '0.72rem', color: 'var(--text-tertiary)', paddingTop: '0.35rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                    <span>Likes: <strong style={{ color: 'var(--text-secondary)' }}>{post.metrics?.likes ?? 0}</strong></span>
                    <span>Reposts: <strong style={{ color: 'var(--text-secondary)' }}>{post.metrics?.shares ?? 0}</strong></span>
                    <span>Replies: <strong style={{ color: 'var(--text-secondary)' }}>{post.metrics?.comments ?? 0}</strong></span>
                    <span>Views: <strong style={{ color: 'var(--text-secondary)' }}>{post.metrics?.views ?? 0}</strong></span>
                  </div>
                </div>
              ))}
            </div>

            {/* Highlight Primary Detected Insight if any */}
            {demoResult.primary_insight && (
              <div
                style={{
                  marginTop: '0.35rem',
                  padding: '0.85rem 1rem',
                  backgroundColor: 'rgba(56, 189, 248, 0.08)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <div style={{ color: 'var(--accent-cyan)' }}>
                    <TrendingUp size={20} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                        Primary Signal Grounded in Seed
                      </span>
                      <Badge variant={demoResult.primary_insight.severity === 'critical' ? 'negative' : 'neutral'} size="sm">
                        {demoResult.primary_insight.severity.toUpperCase()}
                      </Badge>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Confidence: {Math.round(demoResult.primary_insight.confidence * 100)}%
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {demoResult.primary_insight.title}
                    </div>
                  </div>
                </div>

                <Button
                  size="sm"
                  variant="primary"
                  icon={<ArrowRight size={14} />}
                  onClick={() => setSelectedInsight(demoResult.primary_insight!)}
                >
                  Inspect Evidence & AI Explanation
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

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
        insightsData={demoResult ? demoResult.unified_report.batch_insights : insightsData}
        loading={insightsLoading}
        error={insightsError}
        onRefresh={handleRefreshAll}
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
        aiInterpretation={demoResult?.primary_ai_interpretation}
        onClose={() => setSelectedInsight(null)}
      />

      {/* Phase 9.5: Analyze Social Posts Modal */}
      <AnalyzePostModal
        isOpen={isAnalyzeModalOpen}
        onClose={() => setIsAnalyzeModalOpen(false)}
        onSuccess={(result) => {
          setDemoResult(result);
          // If primary insight exists, open explanation drawer for immediate inspection
          if (result.primary_insight) {
            setSelectedInsight(result.primary_insight);
          }
        }}
      />
    </div>
  );
};

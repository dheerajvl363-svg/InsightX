import React, { useState, useMemo } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Info,
  Sparkles,
  Flame,
  Activity,
  TrendingUp,
  ExternalLink,
  ChevronRight,
  Filter,
  CheckCircle2,
  RefreshCw,
  Zap,
} from 'lucide-react';
import type { BatchInsightResult, InsightItem, InsightSeverity, InsightType } from '../../types/api';
import { Card, Badge, Button, Skeleton, ErrorBanner } from '../common';

export interface IntelligenceFeedCardProps {
  insightsData: BatchInsightResult | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onSelectInsight: (insight: InsightItem) => void;
  selectedPlatform?: string;
}

export const IntelligenceFeedCard: React.FC<IntelligenceFeedCardProps> = ({
  insightsData,
  loading,
  error,
  onRefresh,
  onSelectInsight,
  selectedPlatform,
}) => {
  const [severityFilter, setSeverityFilter] = useState<'all' | InsightSeverity>('all');

  const insights = useMemo(() => {
    const list = insightsData?.insights ?? [];
    if (severityFilter === 'all') return list;
    return list.filter((item) => item.severity === severityFilter);
  }, [insightsData, severityFilter]);

  const totalInsights = insightsData?.total_insights ?? 0;
  const criticalCount = insightsData?.critical_count ?? 0;
  const highCount = insightsData?.high_count ?? 0;
  const mediumCount = insightsData?.medium_count ?? 0;
  const lowCount = insightsData?.low_count ?? 0;

  const getSeverityBadge = (sev: InsightSeverity) => {
    switch (sev) {
      case 'critical':
        return { variant: 'negative' as const, label: 'CRITICAL', icon: ShieldAlert, glow: '0 0 10px rgba(255, 82, 82, 0.4)' };
      case 'high':
        return { variant: 'negative' as const, label: 'HIGH', icon: AlertTriangle, glow: 'none' };
      case 'medium':
        return { variant: 'neutral' as const, label: 'MEDIUM', icon: AlertTriangle, glow: 'none' };
      case 'low':
        return { variant: 'cyan' as const, label: 'LOW', icon: Info, glow: 'none' };
      default:
        return { variant: 'default' as const, label: 'INFO', icon: Info, glow: 'none' };
    }
  };

  const getTypeIcon = (type: InsightType) => {
    switch (type) {
      case 'emerging_trend':
        return <Sparkles size={14} color="var(--accent-cyan)" />;
      case 'anomalous_spike':
        return <Flame size={14} color="var(--sentiment-neg)" />;
      case 'sentiment_shift':
        return <Activity size={14} color="var(--sentiment-neu)" />;
      case 'cross_platform_propagation':
        return <TrendingUp size={14} color="var(--accent-purple)" />;
      case 'influencer_amplification':
        return <ExternalLink size={14} color="var(--accent-blue)" />;
      case 'narrative_emergence':
        return <Sparkles size={14} color="var(--accent-cyan)" />;
      case 'engagement_surge':
        return <Flame size={14} color="var(--sentiment-pos)" />;
      default:
        return <Zap size={14} color="var(--accent-cyan)" />;
    }
  };

  const formatTypeName = (type: InsightType) => {
    return String(type)
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  return (
    <Card
      title="Synthesized AI Intelligence & Alert Feed"
      subtitle={`Deterministic evidence-grounded anomaly detection — ${totalInsights} active alerts (${selectedPlatform ? `Filter: ${selectedPlatform}` : 'All Streams'})`}
      headerAction={
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={13} className={loading ? 'animate-spin' : ''} />}
            onClick={onRefresh}
            disabled={loading}
            title="Re-synthesize intelligence"
          >
            Re-Analyze
          </Button>

          <Badge variant="cyan" size="sm">
            Deterministic Engine v7.2
          </Badge>
        </div>
      }
      style={{
        marginBottom: '2rem',
        border: '1px solid rgba(0, 210, 255, 0.25)',
        boxShadow: 'var(--shadow-glow)',
      }}
    >
      {/* Triage Status Bar & Severity Filter Tabs */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '0.85rem 1rem',
          backgroundColor: 'var(--bg-surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
          marginBottom: '1.25rem',
        }}
      >
        {/* Triage Stat Counters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
            Operational Triage:
          </span>

          <span
            onClick={() => setSeverityFilter('critical')}
            style={{
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.2rem 0.6rem',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: criticalCount > 0 ? 'var(--sentiment-neg-bg)' : 'var(--bg-tertiary)',
              color: criticalCount > 0 ? 'var(--sentiment-neg)' : 'var(--text-muted)',
              border: `1px solid ${criticalCount > 0 ? 'rgba(255, 82, 82, 0.3)' : 'var(--border-subtle)'}`,
            }}
          >
            <ShieldAlert size={12} />
            {criticalCount} Critical
          </span>

          <span
            onClick={() => setSeverityFilter('high')}
            style={{
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.2rem 0.6rem',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: highCount > 0 ? 'rgba(255, 112, 67, 0.15)' : 'var(--bg-tertiary)',
              color: highCount > 0 ? '#ff7043' : 'var(--text-muted)',
              border: `1px solid ${highCount > 0 ? 'rgba(255, 112, 67, 0.3)' : 'var(--border-subtle)'}`,
            }}
          >
            <AlertTriangle size={12} />
            {highCount} High
          </span>

          <span
            onClick={() => setSeverityFilter('medium')}
            style={{
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.2rem 0.6rem',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: mediumCount > 0 ? 'var(--sentiment-neu-bg)' : 'var(--bg-tertiary)',
              color: mediumCount > 0 ? 'var(--sentiment-neu)' : 'var(--text-muted)',
              border: `1px solid ${mediumCount > 0 ? 'rgba(255, 177, 66, 0.3)' : 'var(--border-subtle)'}`,
            }}
          >
            {mediumCount} Medium
          </span>

          <span
            onClick={() => setSeverityFilter('low')}
            style={{
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.2rem 0.6rem',
              borderRadius: 'var(--radius-full)',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: lowCount > 0 ? 'var(--accent-cyan-bg)' : 'var(--bg-tertiary)',
              color: lowCount > 0 ? 'var(--accent-cyan)' : 'var(--text-muted)',
              border: `1px solid ${lowCount > 0 ? 'rgba(0, 210, 255, 0.3)' : 'var(--border-subtle)'}`,
            }}
          >
            {lowCount} Low
          </span>
        </div>

        {/* Severity Filter Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Filter size={12} /> Filter:
          </span>
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              style={{
                backgroundColor: severityFilter === sev ? 'var(--accent-cyan-bg)' : 'transparent',
                color: severityFilter === sev ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                border: `1px solid ${severityFilter === sev ? 'rgba(0, 210, 255, 0.4)' : 'transparent'}`,
                borderRadius: 'var(--radius-sm)',
                padding: '0.2rem 0.55rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'all var(--transition-fast)',
              }}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div style={{ marginBottom: '1rem' }}>
          <ErrorBanner
            title="Intelligence Engine Notice"
            message={error}
            onRetry={onRefresh}
          />
        </div>
      )}

      {/* Loading Skeletons */}
      {loading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                padding: '1.25rem',
                borderRadius: 'var(--radius-md)',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Skeleton height={20} width="40%" />
                <Skeleton height={20} width="25%" />
              </div>
              <Skeleton height={24} width="85%" />
              <Skeleton height={40} width="100%" />
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                <Skeleton height={20} width="30%" />
                <Skeleton height={20} width="30%" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && insights.length === 0 && (
        <div
          style={{
            padding: '2.5rem 1.5rem',
            textAlign: 'center',
            backgroundColor: 'var(--bg-surface)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-subtle)',
          }}
        >
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              backgroundColor: 'var(--sentiment-pos-bg)',
              color: 'var(--sentiment-pos)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 0.85rem',
            }}
          >
            <CheckCircle2 size={24} />
          </div>
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
            {severityFilter === 'all'
              ? 'All Social Streams Operating Within Normal Parameters'
              : `No ${severityFilter.toUpperCase()} Severity Alerts Detected`}
          </h4>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-muted)', maxWidth: '520px', margin: '0 auto' }}>
            The deterministic intelligence engine detected no volume spikes or sentiment anomalies exceeding critical thresholds for the active observation window.
          </p>
        </div>
      )}

      {/* Active Insights Grid */}
      {!loading && insights.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {insights.map((insight) => {
            const sevBadge = getSeverityBadge(insight.severity);
            const SevIcon = sevBadge.icon;
            const confidencePct = Math.round(insight.confidence * 100);

            return (
              <div
                key={insight.id}
                onClick={() => onSelectInsight(insight)}
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  border: `1px solid ${insight.severity === 'critical' ? 'rgba(255, 82, 82, 0.4)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  boxShadow: insight.severity === 'critical' ? '0 0 12px rgba(255, 82, 82, 0.15)' : 'var(--shadow-sm)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor =
                    insight.severity === 'critical' ? 'rgba(255, 82, 82, 0.4)' : 'var(--border-subtle)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div>
                  {/* Card Header: Severity & Type Tags */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <Badge variant={sevBadge.variant} size="sm" icon={<SevIcon size={12} />} style={{ boxShadow: sevBadge.glow }}>
                        {sevBadge.label}
                      </Badge>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        {getTypeIcon(insight.type)}
                        <span>{formatTypeName(insight.type)}</span>
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>CONF:</span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: confidencePct >= 75 ? 'var(--sentiment-pos)' : 'var(--sentiment-neu)',
                        }}
                      >
                        {confidencePct}%
                      </span>
                    </div>
                  </div>

                  {/* Insight Title */}
                  <h4
                    style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      lineHeight: 1.35,
                      marginBottom: '0.5rem',
                    }}
                  >
                    {insight.title}
                  </h4>

                  {/* Concise Summary / Interpretation */}
                  <p
                    style={{
                      fontSize: '0.825rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.45,
                      marginBottom: '0.9rem',
                    }}
                  >
                    {insight.summary}
                  </p>

                  {/* Grounded Key Metrics Chips */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.9rem' }}>
                    {insight.evidence?.growth_rate !== null && insight.evidence?.growth_rate !== undefined && (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '0.15rem 0.45rem',
                          borderRadius: 'var(--radius-xs)',
                          backgroundColor: 'var(--bg-tertiary)',
                          color: (insight.evidence.growth_rate ?? 0) >= 0 ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)',
                          fontWeight: 600,
                        }}
                      >
                        Growth: {(insight.evidence.growth_rate ?? 0) >= 0 ? '+' : ''}{((insight.evidence.growth_rate ?? 0) * 100).toFixed(0)}%
                      </span>
                    )}

                    {insight.evidence?.current_volume !== null && insight.evidence?.current_volume !== undefined && (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '0.15rem 0.45rem',
                          borderRadius: 'var(--radius-xs)',
                          backgroundColor: 'var(--bg-tertiary)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        Vol: {insight.evidence.current_volume} posts
                      </span>
                    )}

                    {insight.evidence?.z_score !== null && insight.evidence?.z_score !== undefined && (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '0.15rem 0.45rem',
                          borderRadius: 'var(--radius-xs)',
                          backgroundColor: 'var(--bg-tertiary)',
                          color: 'var(--sentiment-neg)',
                          fontWeight: 600,
                        }}
                      >
                        +{insight.evidence.z_score.toFixed(1)}σ Spike
                      </span>
                    )}

                    {insight.evidence?.sentiment_score !== null && insight.evidence?.sentiment_score !== undefined && (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '0.15rem 0.45rem',
                          borderRadius: 'var(--radius-xs)',
                          backgroundColor: 'var(--bg-tertiary)',
                          color: (insight.evidence.sentiment_score ?? 0) >= 0 ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)',
                        }}
                      >
                        Polarity: {(insight.evidence.sentiment_score ?? 0) >= 0 ? '+' : ''}{insight.evidence.sentiment_score.toFixed(2)}
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Footer: Context Badges & Action Link */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    paddingTop: '0.75rem',
                    borderTop: '1px solid var(--border-subtle)',
                    marginTop: '0.5rem',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                    {insight.affected_platforms?.slice(0, 3).map((p) => (
                      <Badge key={p} variant="default" size="sm">
                        {p}
                      </Badge>
                    ))}
                    {insight.affected_topic && (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        #{insight.affected_topic}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectInsight(insight);
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.2rem 0',
                    }}
                  >
                    <span>Explain & Trace</span>
                    <ChevronRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};

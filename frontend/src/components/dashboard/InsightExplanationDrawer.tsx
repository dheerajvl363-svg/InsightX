import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  ShieldAlert,
  AlertTriangle,
  Info,
  CheckCircle2,
  TrendingUp,
  Flame,
  Activity,
  Sparkles,
  ArrowRight,
  ExternalLink,
  Database,
  CheckSquare,
  Square,
  Clock,
  FileCheck2,
  Bot,
} from 'lucide-react';
import { useInsightExplanation } from '../../hooks/useInsightExplanation';
import type { InsightItem, InsightSeverity, InsightType } from '../../types/api';
import { Badge, Button, Skeleton, ErrorBanner } from '../common';

export interface InsightExplanationDrawerProps {
  insight: InsightItem | null;
  platform?: string;
  aiInterpretation?: Record<string, unknown> | null;
  onClose: () => void;
}

export const InsightExplanationDrawer: React.FC<InsightExplanationDrawerProps> = ({
  insight,
  platform,
  aiInterpretation,
  onClose,
}) => {
  const navigate = useNavigate();
  const [completedItems, setCompletedItems] = useState<Record<number, boolean>>({});

  // Fetch deep explanation and auditable trace from backend
  const {
    data: explanation,
    loading,
    error,
    refetch,
  } = useInsightExplanation(insight?.id || null, platform);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Reset checklist when switching insights
  useEffect(() => {
    setCompletedItems({});
  }, [insight?.id]);

  if (!insight) return null;

  const toggleActionItem = (index: number) => {
    setCompletedItems((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const getSeverityVariant = (sev: InsightSeverity) => {
    switch (sev) {
      case 'critical':
        return { variant: 'negative' as const, label: 'CRITICAL ALERT', icon: ShieldAlert, glow: '0 0 16px rgba(255, 82, 82, 0.4)' };
      case 'high':
        return { variant: 'negative' as const, label: 'HIGH PRIORITY', icon: AlertTriangle, glow: '0 0 12px rgba(255, 82, 82, 0.25)' };
      case 'medium':
        return { variant: 'neutral' as const, label: 'MEDIUM PRIORITY', icon: AlertTriangle, glow: 'none' };
      case 'low':
        return { variant: 'cyan' as const, label: 'LOW / MONITOR', icon: Info, glow: 'none' };
      default:
        return { variant: 'default' as const, label: 'INFORMATIONAL', icon: Info, glow: 'none' };
    }
  };

  const getTypeLabel = (type: InsightType) => {
    switch (type) {
      case 'emerging_trend':
        return { label: 'Emerging Trend', icon: Sparkles };
      case 'anomalous_spike':
        return { label: 'Anomalous Volume Spike', icon: Flame };
      case 'sentiment_shift':
        return { label: 'Sentiment Polarity Shift', icon: Activity };
      case 'cross_platform_propagation':
        return { label: 'Cross-Platform Propagation', icon: TrendingUp };
      case 'influencer_amplification':
        return { label: 'Influencer Amplification', icon: ExternalLink };
      case 'narrative_emergence':
        return { label: 'Narrative Emergence', icon: Sparkles };
      case 'engagement_surge':
        return { label: 'Engagement Velocity Surge', icon: Flame };
      case 'data_quality_alert':
        return { label: 'Data Integrity Alert', icon: ShieldAlert };
      default:
        return { label: String(type).replace(/_/g, ' '), icon: Info };
    }
  };

  const sevInfo = getSeverityVariant(insight.severity);
  const typeInfo = getTypeLabel(insight.type);
  const TypeIcon = typeInfo.icon;
  const SevIcon = sevInfo.icon;

  const confidencePct = Math.round(insight.confidence * 100);

  // Drilldown handler into Posts Explorer
  const handleDrilldownPosts = () => {
    const topic = insight.affected_topic || insight.evidence?.topic_label;
    const targetPlatform =
      insight.affected_platforms?.[0] || insight.evidence?.platforms?.[0] || platform;

    const params = new URLSearchParams();
    if (topic) params.append('search', topic);
    if (targetPlatform && targetPlatform !== 'all') params.append('platform', targetPlatform);

    onClose();
    navigate(`/posts?${params.toString()}`);
  };

  // Drilldown handler into Timeline Radar
  const handleDrilldownTimeline = () => {
    const targetPlatform =
      insight.affected_platforms?.[0] || insight.evidence?.platforms?.[0] || platform;
    const qs = targetPlatform && targetPlatform !== 'all' ? `?platform=${targetPlatform}` : '';
    onClose();
    navigate(`/timeline${qs}`);
  };

  const activeExplanation = explanation;
  const facts = activeExplanation?.facts || [];
  const actionItems = activeExplanation?.action_items || insight.action_items || [];
  const recommendedAction = activeExplanation?.recommended_action || insight.recommended_action;
  const interpretation = activeExplanation?.interpretation || insight.summary;
  const confidenceRationale = activeExplanation?.confidence_rationale;
  const severityRationale = activeExplanation?.severity_rationale;
  const evidenceRefs = activeExplanation?.evidence_references;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(5, 8, 16, 0.78)',
          backdropFilter: 'blur(6px)',
          zIndex: 'var(--z-drawer)',
          animation: 'fadeIn var(--transition-fast)',
        }}
      />

      {/* Drawer Panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '560px',
          backgroundColor: 'var(--bg-secondary)',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-lg)',
          zIndex: 'calc(var(--z-drawer) + 1)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'slideInRight var(--transition-normal)',
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
              <Badge variant={sevInfo.variant} size="sm" icon={<SevIcon size={12} />} style={{ boxShadow: sevInfo.glow }}>
                {sevInfo.label}
              </Badge>
              <Badge variant="default" size="sm" icon={<TypeIcon size={12} />}>
                {typeInfo.label}
              </Badge>
              <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                {insight.id}
              </span>
            </div>

            <h2
              style={{
                fontSize: '1.2rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.3,
                letterSpacing: '-0.01em',
              }}
            >
              {insight.title}
            </h2>
          </div>

          <button
            onClick={onClose}
            aria-label="Close explanation drawer"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.35rem',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'color var(--transition-fast)',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Scrollable Body */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
          }}
        >
          {/* Error Banner if Explanation API Failed */}
          {error && (
            <ErrorBanner
              title="Failed to Load Detailed Explanation"
              message={error}
              onRetry={refetch}
            />
          )}

          {/* Statistical Confidence & Severity Metric Cards */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '1rem',
            }}
          >
            {/* Confidence Card */}
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Confidence Score
                </span>
                <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                  {confidencePct}%
                </span>
              </div>
              <div
                style={{
                  height: '6px',
                  backgroundColor: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-full)',
                  overflow: 'hidden',
                  marginBottom: '0.5rem',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${confidencePct}%`,
                    backgroundColor: confidencePct >= 75 ? 'var(--sentiment-pos)' : confidencePct >= 50 ? 'var(--sentiment-neu)' : 'var(--sentiment-neg)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.3 }}>
                {loading ? <Skeleton height={14} width="90%" /> : confidenceRationale || `Statistical confidence computed by deterministic intelligence engine.`}
              </p>
            </div>

            {/* Severity Card */}
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Triage Severity
                </span>
                <span
                  style={{
                    fontSize: '0.95rem',
                    fontWeight: 700,
                    color: insight.severity === 'critical' ? 'var(--sentiment-neg)' : insight.severity === 'high' ? 'var(--sentiment-neg)' : 'var(--sentiment-neu)',
                    textTransform: 'uppercase',
                  }}
                >
                  {insight.severity}
                </span>
              </div>
              <div style={{ marginTop: '0.5rem' }}>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.3 }}>
                  {loading ? <Skeleton height={14} width="90%" /> : severityRationale || `Operational severity determined by volume anomalies and impact velocity.`}
                </p>
              </div>
            </div>
          </div>

          {/* Section 1: Grounded Verifiable Facts */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <FileCheck2 size={16} color="var(--sentiment-pos)" />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Verifiable Grounded Facts
              </h3>
              <Badge variant="positive" size="sm">Audited</Badge>
            </div>

            {loading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <Skeleton height={16} width="100%" />
                <Skeleton height={16} width="85%" />
                <Skeleton height={16} width="92%" />
              </div>
            ) : facts.length > 0 ? (
              <ul style={{ margin: 0, paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                {facts.map((fact, idx) => (
                  <li key={idx} style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.45 }}>
                    {fact}
                  </li>
                ))}
              </ul>
            ) : (
              <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                {insight.summary}
              </div>
            )}
          </div>

          {/* Section 2: Strategic Interpretation */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <Sparkles size={16} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Strategic Interpretation
              </h3>
            </div>

            {loading ? (
              <Skeleton height={40} width="100%" />
            ) : (
              <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {interpretation}
              </p>
            )}
          </div>

          {/* Section 3: Recommended Operational Action & Checklist */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid rgba(0, 210, 255, 0.25)',
              borderRadius: 'var(--radius-md)',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.65rem' }}>
              <CheckCircle2 size={16} color="var(--accent-cyan)" />
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Recommended Operational Directive
              </h3>
            </div>

            {recommendedAction && (
              <div
                style={{
                  backgroundColor: 'var(--accent-cyan-bg)',
                  border: '1px solid rgba(0, 210, 255, 0.2)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem',
                  fontSize: '0.85rem',
                  fontWeight: 500,
                  color: 'var(--text-primary)',
                  marginBottom: '1rem',
                  lineHeight: 1.4,
                }}
              >
                {recommendedAction}
              </div>
            )}

            {actionItems.length > 0 && (
              <div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  Analyst Triage Checklist ({Object.values(completedItems).filter(Boolean).length}/{actionItems.length} complete)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {actionItems.map((item, idx) => {
                    const isDone = Boolean(completedItems[idx]);
                    return (
                      <div
                        key={idx}
                        onClick={() => toggleActionItem(idx)}
                        style={{
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '0.6rem',
                          padding: '0.5rem 0.65rem',
                          borderRadius: 'var(--radius-sm)',
                          backgroundColor: isDone ? 'rgba(0, 230, 118, 0.08)' : 'var(--bg-tertiary)',
                          border: `1px solid ${isDone ? 'rgba(0, 230, 118, 0.25)' : 'var(--border-subtle)'}`,
                          cursor: 'pointer',
                          transition: 'all var(--transition-fast)',
                        }}
                      >
                        <span style={{ color: isDone ? 'var(--sentiment-pos)' : 'var(--text-muted)', marginTop: '2px' }}>
                          {isDone ? <CheckSquare size={16} /> : <Square size={16} />}
                        </span>
                        <span
                          style={{
                            fontSize: '0.825rem',
                            color: isDone ? 'var(--text-muted)' : 'var(--text-primary)',
                            textDecoration: isDone ? 'line-through' : 'none',
                            lineHeight: 1.35,
                          }}
                        >
                          {item}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Dedicated Card: AI Qualitative Interpretation */}
          {(() => {
            const activeAi =
              aiInterpretation ||
              (insight?.metadata?.ai_analysis as Record<string, unknown> | undefined) ||
              ((explanation as unknown as Record<string, unknown>)?.ai_analysis as Record<string, unknown> | undefined);

            if (!activeAi) {
              return (
                <div
                  style={{
                    backgroundColor: 'rgba(15, 23, 42, 0.4)',
                    border: '1px dashed var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.85rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.65rem',
                  }}
                >
                  <Bot size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    AI qualitative interpretation is optional or not generated for this insight. Showing deterministic evidence-based explanation.
                  </span>
                </div>
              );
            }

            const interpretationText = (activeAi.interpretation as string) || '';
            const aiRecommendations = (activeAi.ai_recommendations as string[]) || [];
            const confidenceAssessment = (activeAi.confidence_assessment as string) || '';
            const groundingMeta = (activeAi.grounding_metadata as Record<string, unknown>) || {};
            const isFullyGrounded = groundingMeta.is_fully_grounded !== false;
            const providerName = (activeAi.provider_name as string) || 'AI Assistant';
            const modelName = (activeAi.model_name as string) || 'insightx-ai-v1';
            const disclaimerText =
              (activeAi.disclaimer as string) ||
              'AI qualitative interpretation assistant. Deterministic analytics and evidence remain the source of truth.';

            return (
              <div
                style={{
                  backgroundColor: 'rgba(24, 19, 45, 0.55)',
                  border: '1px solid rgba(168, 85, 247, 0.35)',
                  borderRadius: 'var(--radius-md)',
                  padding: '1.25rem',
                  boxShadow: '0 4px 16px rgba(168, 85, 247, 0.08)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
                    <Bot size={18} style={{ color: 'var(--accent-purple)' }} />
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                      AI Qualitative Interpretation
                    </h3>
                  </div>
                  <Badge variant={isFullyGrounded ? 'primary' : 'neutral'} size="sm">
                    {isFullyGrounded ? 'Evidence-Grounded' : 'Fallback Safe'}
                  </Badge>
                </div>

                {/* Visible Mandatory Disclaimer */}
                <div
                  style={{
                    backgroundColor: 'rgba(168, 85, 247, 0.12)',
                    border: '1px solid rgba(168, 85, 247, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.55rem 0.75rem',
                    marginBottom: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <Sparkles size={14} style={{ color: 'var(--accent-purple)', flexShrink: 0 }} />
                  <span style={{ fontSize: '0.74rem', color: 'var(--text-primary)', lineHeight: 1.35, fontWeight: 500 }}>
                    {disclaimerText}
                  </span>
                </div>

                {/* Narrative Synthesis */}
                {interpretationText && (
                  <div style={{ marginBottom: '0.85rem' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
                      Narrative Synthesis
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.45, margin: 0 }}>
                      {interpretationText}
                    </p>
                  </div>
                )}

                {/* AI Recommendations */}
                {aiRecommendations.length > 0 && (
                  <div style={{ marginBottom: '0.85rem' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.35rem' }}>
                      AI Strategic Recommendations
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                      {aiRecommendations.map((rec, idx) => (
                        <li key={idx} style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Confidence & Nuance Assessment */}
                {confidenceAssessment && (
                  <div style={{ marginBottom: '0.85rem' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.25rem' }}>
                      Nuance & Uncertainty Assessment
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', lineHeight: 1.4, margin: 0, fontStyle: 'italic' }}>
                      "{confidenceAssessment}"
                    </p>
                  </div>
                )}

                {/* AI Provider & Model Tag */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.5rem', borderTop: '1px solid rgba(255, 255, 255, 0.06)', fontSize: '0.72rem', color: 'var(--text-tertiary)' }}>
                  <span>Provider: <strong style={{ color: 'var(--text-secondary)' }}>{providerName}</strong></span>
                  <span>Model: <code style={{ color: 'var(--accent-purple)' }}>{modelName}</code></span>
                </div>
              </div>
            );
          })()}

          {/* Section 4: Evidence & Traceability Metrics */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '1.25rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Database size={16} color="var(--accent-purple)" />
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Supporting Evidence & Provenance
                </h3>
              </div>
              <Badge variant="cyan" size="sm">Deterministic Trace</Badge>
            </div>

            {/* Grounded Evidence Chips */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.65rem', marginBottom: '1rem' }}>
              {insight.evidence?.growth_rate !== null && insight.evidence?.growth_rate !== undefined && (
                <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Growth Rate</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: (insight.evidence.growth_rate ?? 0) >= 0 ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)' }}>
                    {(insight.evidence.growth_rate ?? 0) >= 0 ? '+' : ''}{((insight.evidence.growth_rate ?? 0) * 100).toFixed(0)}%
                  </div>
                </div>
              )}

              {insight.evidence?.current_volume !== null && insight.evidence?.current_volume !== undefined && (
                <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Current Volume</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {insight.evidence.current_volume} posts
                  </div>
                </div>
              )}

              {insight.evidence?.baseline_volume !== null && insight.evidence?.baseline_volume !== undefined && (
                <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Baseline Volume</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                    {insight.evidence.baseline_volume} posts
                  </div>
                </div>
              )}

              {insight.evidence?.z_score !== null && insight.evidence?.z_score !== undefined && (
                <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Z-Score</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--sentiment-neg)' }}>
                    +{insight.evidence.z_score.toFixed(2)}σ
                  </div>
                </div>
              )}

              {insight.evidence?.sentiment_score !== null && insight.evidence?.sentiment_score !== undefined && (
                <div style={{ backgroundColor: 'var(--bg-tertiary)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Polarity Score</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, color: (insight.evidence.sentiment_score ?? 0) >= 0 ? 'var(--sentiment-pos)' : 'var(--sentiment-neg)' }}>
                    {(insight.evidence.sentiment_score ?? 0) >= 0 ? '+' : ''}{insight.evidence.sentiment_score.toFixed(2)} NSS
                  </div>
                </div>
              )}
            </div>

            {/* Supporting Platforms & Post IDs */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {(insight.affected_platforms && insight.affected_platforms.length > 0) && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Platforms:</span>
                  {insight.affected_platforms.map((p) => (
                    <Badge key={p} variant="default" size="sm">{p}</Badge>
                  ))}
                </div>
              )}

              {insight.affected_topic && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Topic Cluster:</span>
                  <Badge variant="primary" size="sm">{insight.affected_topic}</Badge>
                </div>
              )}

              {(evidenceRefs?.post_ids && evidenceRefs.post_ids.length > 0) && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Linked Database Post IDs:</span>
                  <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginTop: '0.3rem' }}>
                    {evidenceRefs.post_ids.slice(0, 10).map((pid) => (
                      <span
                        key={pid}
                        onClick={() => {
                          onClose();
                          navigate(`/posts?search=${pid}`);
                        }}
                        style={{
                          backgroundColor: 'var(--bg-tertiary)',
                          padding: '0.15rem 0.45rem',
                          borderRadius: 'var(--radius-xs)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.75rem',
                          color: 'var(--accent-cyan)',
                          cursor: 'pointer',
                        }}
                        title={`Click to search post ${pid} in Explorer`}
                      >
                        #{pid}
                      </span>
                    ))}
                    {evidenceRefs.post_ids.length > 10 && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        +{evidenceRefs.post_ids.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Drawer Footer Actions */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            <Clock size={14} />
            <span>
              Generated {new Date(insight.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Button size="sm" variant="secondary" onClick={handleDrilldownTimeline}>
              View in Timeline
            </Button>
            <Button size="sm" variant="primary" icon={<ArrowRight size={14} />} onClick={handleDrilldownPosts}>
              Explore Supporting Posts
            </Button>
          </div>
        </div>
      </div>
    </>
  );
};

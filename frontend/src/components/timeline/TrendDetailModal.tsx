import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  TrendingUp,
  Flame,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight,
  Minus,
  Calendar,
  Layers,
  Activity,
} from 'lucide-react';
import type { TopicTrendResult } from '../../types/api';
import { Badge, Button } from '../common';

interface TrendDetailModalProps {
  trend: TopicTrendResult | null;
  onClose: () => void;
}

export const TrendDetailModal: React.FC<TrendDetailModalProps> = ({ trend, onClose }) => {
  const navigate = useNavigate();
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!trend) return null;

  const getDirectionBadge = (direction: string) => {
    switch (direction) {
      case 'spiking':
        return { variant: 'negative' as const, label: 'Spiking Surge', icon: Flame };
      case 'emerging':
        return { variant: 'cyan' as const, label: 'Emerging Signal', icon: Sparkles };
      case 'growing':
        return { variant: 'positive' as const, label: 'Growing Trend', icon: ArrowUpRight };
      case 'declining':
        return { variant: 'neutral' as const, label: 'Declining', icon: ArrowDownRight };
      default:
        return { variant: 'neutral' as const, label: 'Stable', icon: Minus };
    }
  };

  const dirBadge = getDirectionBadge(trend.direction);
  const DirectionIcon = dirBadge.icon;

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short',
    });
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(5, 8, 16, 0.75)',
          backdropFilter: 'blur(4px)',
          zIndex: 'var(--z-modal)',
          animation: 'fadeIn 0.2s ease-out',
        }}
      />

      {/* Modal Dialog */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '90%',
          maxWidth: '640px',
          maxHeight: '90vh',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)',
          zIndex: 'calc(var(--z-modal) + 1)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeIn 0.25s ease-out',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--accent-purple-bg)',
                color: 'var(--accent-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <TrendingUp size={18} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {trend.topic_label}
              </h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Topic ID: {trend.topic_id}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.4rem',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
            }}
            title="Close (Esc)"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '1.5rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Key Indicators Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
            <div
              style={{
                padding: '0.85rem 1rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Direction</span>
              <div style={{ marginTop: '0.35rem' }}>
                <Badge variant={dirBadge.variant} size="sm">
                  <DirectionIcon size={12} style={{ marginRight: '0.3rem', display: 'inline' }} />
                  {dirBadge.label}
                </Badge>
              </div>
            </div>

            <div
              style={{
                padding: '0.85rem 1rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Growth Rate</span>
              <span
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  color: trend.growth_rate > 0 ? 'var(--sentiment-pos)' : trend.growth_rate < 0 ? 'var(--sentiment-neg)' : 'var(--text-primary)',
                  display: 'block',
                  marginTop: '0.2rem',
                }}
              >
                {trend.growth_rate >= 0 ? '+' : ''}{trend.growth_rate.toFixed(1)}%
              </span>
            </div>

            <div
              style={{
                padding: '0.85rem 1rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Trend Score</span>
              <span
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--accent-cyan)',
                  display: 'block',
                  marginTop: '0.2rem',
                }}
              >
                {trend.trend_score.toFixed(3)}
              </span>
            </div>
          </div>

          {/* Volume Breakdown Card */}
          <div
            style={{
              padding: '1rem 1.25rem',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Volume Comparison
            </span>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current Evaluation Window</span>
                <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                  {trend.current_volume.toLocaleString()} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>posts</span>
                </div>
              </div>
              <div style={{ height: '32px', width: '1px', backgroundColor: 'var(--border-subtle)' }} />
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Reference Baseline Window</span>
                <div style={{ fontSize: '1.35rem', fontWeight: 700, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                  {trend.baseline_volume.toLocaleString()} <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>posts</span>
                </div>
              </div>
            </div>
          </div>

          {/* Time Window Specifications */}
          <div
            style={{
              padding: '1rem 1.25rem',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.65rem',
              fontSize: '0.825rem',
            }}
          >
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Evaluation Windows
            </span>
            {trend.current_window && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Calendar size={13} /> Current Window
                </span>
                <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                  {formatDate(trend.current_window.start)} &rarr; {formatDate(trend.current_window.end)}
                </span>
              </div>
            )}
            {trend.baseline_window && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Calendar size={13} /> Baseline Window
                </span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                  {formatDate(trend.baseline_window.start)} &rarr; {formatDate(trend.baseline_window.end)}
                </span>
              </div>
            )}
          </div>

          {/* Statistical Signals & Details */}
          {trend.details && Object.keys(trend.details).length > 0 && (
            <div
              style={{
                padding: '1rem 1.25rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <Activity size={14} color="var(--accent-cyan)" /> Statistical Telemetry Signals
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.5rem' }}>
                {Object.entries(trend.details).map(([k, v]) => (
                  <div key={k} style={{ padding: '0.5rem 0.75rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'block', textTransform: 'capitalize' }}>
                      {k.replace(/_/g, ' ')}
                    </span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                      {typeof v === 'number' ? v.toFixed(3) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Member Post IDs */}
          {trend.post_ids && trend.post_ids.length > 0 && (
            <div
              style={{
                padding: '1rem 1.25rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <Layers size={14} color="var(--accent-purple)" /> Member Post Evidence ({trend.post_ids.length})
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                {trend.post_ids.map((id) => (
                  <span
                    key={id}
                    style={{
                      padding: '0.2rem 0.5rem',
                      backgroundColor: 'var(--bg-tertiary)',
                      borderRadius: 'var(--radius-xs)',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--accent-cyan)',
                    }}
                  >
                    #{id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-surface)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Button
            size="sm"
            variant="primary"
            icon={<ArrowRight size={14} />}
            onClick={() => {
              onClose();
              navigate(`/posts?search=${encodeURIComponent(trend.topic_label)}`);
            }}
          >
            Explore Evidence Posts
          </Button>

          <Button size="sm" variant="secondary" onClick={onClose}>
            Close Inspector
          </Button>
        </div>
      </div>
    </>
  );
};

import React from 'react';
import { Skeleton } from './Skeleton';

export interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  iconBg?: string;
  iconColor?: string;
  badge?: React.ReactNode;
  subtext?: string;
  loading?: boolean;
  style?: React.CSSProperties;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  iconBg = 'var(--accent-cyan-bg)',
  iconColor = 'var(--accent-cyan)',
  badge,
  subtext,
  loading = false,
  style = {},
}) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.35rem 1.5rem',
        boxShadow: 'var(--shadow-card)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
          {label}
        </span>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: iconBg,
            color: iconColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {icon}
        </div>
      </div>

      <div>
        {loading ? (
          <Skeleton width="60%" height="2rem" style={{ marginBottom: '0.5rem' }} />
        ) : (
          <div
            style={{
              fontSize: '1.85rem',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.02em',
              lineHeight: 1.15,
              marginBottom: '0.4rem',
            }}
          >
            {value}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem', flexWrap: 'wrap' }}>
          {subtext && (
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              {subtext}
            </span>
          )}
          {badge && <div>{badge}</div>}
        </div>
      </div>
    </div>
  );
};

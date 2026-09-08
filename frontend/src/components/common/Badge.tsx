import React from 'react';

export type BadgeVariant =
  | 'default'
  | 'primary'
  | 'cyan'
  | 'positive'
  | 'neutral'
  | 'negative'
  | 'x'
  | 'reddit'
  | 'telegram'
  | 'youtube';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const variantStyles: Record<BadgeVariant, React.CSSProperties> = {
  default: {
    color: 'var(--text-secondary)',
    backgroundColor: 'var(--bg-tertiary)',
    borderColor: 'var(--border-subtle)',
  },
  primary: {
    color: 'var(--accent-blue)',
    backgroundColor: 'rgba(59, 130, 246, 0.12)',
    borderColor: 'rgba(59, 130, 246, 0.25)',
  },
  cyan: {
    color: 'var(--accent-cyan)',
    backgroundColor: 'var(--accent-cyan-bg)',
    borderColor: 'rgba(0, 210, 255, 0.25)',
  },
  positive: {
    color: 'var(--sentiment-pos)',
    backgroundColor: 'var(--sentiment-pos-bg)',
    borderColor: 'rgba(0, 230, 118, 0.25)',
  },
  neutral: {
    color: 'var(--sentiment-neu)',
    backgroundColor: 'var(--sentiment-neu-bg)',
    borderColor: 'rgba(255, 177, 66, 0.25)',
  },
  negative: {
    color: 'var(--sentiment-neg)',
    backgroundColor: 'var(--sentiment-neg-bg)',
    borderColor: 'rgba(255, 82, 82, 0.25)',
  },
  x: {
    color: 'var(--platform-x)',
    backgroundColor: 'var(--platform-x-bg)',
    borderColor: 'rgba(29, 161, 242, 0.25)',
  },
  reddit: {
    color: 'var(--platform-reddit)',
    backgroundColor: 'var(--platform-reddit-bg)',
    borderColor: 'rgba(255, 69, 0, 0.25)',
  },
  telegram: {
    color: 'var(--platform-telegram)',
    backgroundColor: 'var(--platform-telegram-bg)',
    borderColor: 'rgba(34, 158, 217, 0.25)',
  },
  youtube: {
    color: 'var(--platform-youtube)',
    backgroundColor: 'var(--platform-youtube-bg)',
    borderColor: 'rgba(255, 0, 0, 0.25)',
  },
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  icon,
  className = '',
  style = {},
}) => {
  const currentVariant = variantStyles[variant] || variantStyles.default;
  const isSm = size === 'sm';

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.35rem',
        padding: isSm ? '0.15rem 0.5rem' : '0.25rem 0.65rem',
        borderRadius: 'var(--radius-full)',
        fontSize: isSm ? '0.7rem' : '0.78rem',
        fontWeight: 600,
        letterSpacing: '0.03em',
        border: '1px solid',
        lineHeight: 1.3,
        whiteSpace: 'nowrap',
        ...currentVariant,
        ...style,
      }}
    >
      {icon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</span>}
      <span>{children}</span>
    </span>
  );
};

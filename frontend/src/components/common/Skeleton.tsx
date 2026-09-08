import React from 'react';

export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1rem',
  borderRadius = 'var(--radius-sm)',
  className = '',
  style = {},
}) => {
  return (
    <div
      className={`animate-pulse ${className}`}
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'var(--bg-tertiary)',
        ...style,
      }}
    />
  );
};

export const CardSkeleton: React.FC<{ height?: string | number }> = ({ height = '200px' }) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        height,
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      <Skeleton width="40%" height="1.25rem" />
      <Skeleton width="70%" height="0.9rem" />
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Skeleton width="90%" height="60%" borderRadius="var(--radius-md)" />
      </div>
    </div>
  );
};

import React from 'react';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  loading?: boolean;
}

const variantStyles: Record<ButtonVariant, React.CSSProperties> = {
  primary: {
    backgroundColor: 'var(--accent-cyan)',
    color: 'var(--text-inverse)',
    border: '1px solid var(--accent-cyan)',
    fontWeight: 600,
  },
  secondary: {
    backgroundColor: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-subtle)',
    fontWeight: 500,
  },
  outline: {
    backgroundColor: 'transparent',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-muted)',
    fontWeight: 500,
  },
  ghost: {
    backgroundColor: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid transparent',
    fontWeight: 500,
  },
  danger: {
    backgroundColor: 'rgba(255, 82, 82, 0.15)',
    color: 'var(--sentiment-neg)',
    border: '1px solid rgba(255, 82, 82, 0.3)',
    fontWeight: 600,
  },
};

const sizeStyles: Record<ButtonSize, React.CSSProperties> = {
  sm: {
    padding: '0.35rem 0.75rem',
    fontSize: '0.8rem',
    gap: '0.35rem',
    borderRadius: 'var(--radius-sm)',
  },
  md: {
    padding: '0.55rem 1rem',
    fontSize: '0.875rem',
    gap: '0.5rem',
    borderRadius: 'var(--radius-md)',
  },
  lg: {
    padding: '0.75rem 1.35rem',
    fontSize: '1rem',
    gap: '0.6rem',
    borderRadius: 'var(--radius-md)',
  },
};

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  iconRight,
  loading = false,
  disabled = false,
  style = {},
  className = '',
  ...props
}) => {
  const currentVariant = variantStyles[variant];
  const currentSize = sizeStyles[size];

  return (
    <button
      disabled={disabled || loading}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all var(--transition-fast)',
        outline: 'none',
        fontFamily: 'var(--font-sans)',
        whiteSpace: 'nowrap',
        ...currentSize,
        ...currentVariant,
        ...style,
      }}
      {...props}
    >
      {loading ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        icon && <span style={{ display: 'inline-flex', alignItems: 'center' }}>{icon}</span>
      )}
      {children && <span>{children}</span>}
      {!loading && iconRight && (
        <span style={{ display: 'inline-flex', alignItems: 'center' }}>{iconRight}</span>
      )}
    </button>
  );
};

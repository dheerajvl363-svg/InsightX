import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquareText,
  TrendingUp,
  Share2,
  Activity,
  Radio,
  ExternalLink,
  X,
} from 'lucide-react';
import { Badge } from '../common/Badge';

export interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  const navItems = [
    { to: '/dashboard', label: 'Executive Overview', icon: LayoutDashboard },
    { to: '/timeline', label: 'Timeline & Trends', icon: TrendingUp },
    { to: '/posts', label: 'Posts Explorer', icon: MessageSquareText },
    { to: '/network', label: 'Network Graph', icon: Share2 },
    { to: '/health', label: 'System Health', icon: Activity },
  ];

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      {/* Brand Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '2rem',
          padding: '0 0.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #00d2ff, #3b82f6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#0a0e1a',
              boxShadow: 'var(--shadow-glow)',
            }}
          >
            <Radio size={20} />
          </div>
          <div>
            <h1
              style={{
                fontSize: '1.15rem',
                fontWeight: 700,
                letterSpacing: '-0.02em',
                color: 'var(--text-primary)',
              }}
            >
              Insight<span style={{ color: 'var(--accent-cyan)' }}>X</span>
            </h1>
            <div
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                fontWeight: 600,
              }}
            >
              SIH PS 26152
            </div>
          </div>
        </div>

        {/* Mobile Close Button */}
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              padding: '0.4rem',
            }}
            className="mobile-close-btn"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Navigation Menu */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        <div
          style={{
            fontSize: '0.7rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
            padding: '0 0.75rem 0.25rem',
            fontWeight: 600,
          }}
        >
          Analytics Suite
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--accent-cyan-bg)' : 'transparent',
                fontWeight: isActive ? 600 : 500,
                textDecoration: 'none',
                transition: 'all var(--transition-fast)',
                border: isActive ? '1px solid rgba(0, 210, 255, 0.25)' : '1px solid transparent',
              })}
            >
              <Icon size={18} />
              <span style={{ fontSize: '0.88rem' }}>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Platform Connectors Discovery */}
      <div style={{ marginTop: '2rem', padding: '0 0.5rem' }}>
        <div
          style={{
            fontSize: '0.7rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-muted)',
            marginBottom: '0.6rem',
            fontWeight: 600,
          }}
        >
          Active Feeds
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          <Badge variant="x" size="sm">X (Twitter)</Badge>
          <Badge variant="reddit" size="sm">Reddit</Badge>
          <Badge variant="telegram" size="sm">Telegram</Badge>
          <Badge variant="youtube" size="sm">YouTube</Badge>
        </div>
      </div>

      {/* Sidebar Footer */}
      <div
        style={{
          marginTop: 'auto',
          padding: '1.25rem 0.5rem 0',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: 'var(--sentiment-pos)',
                boxShadow: '0 0 8px var(--sentiment-pos)',
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              API Gateway
            </span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            v5.1.0
          </span>
        </div>

        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.78rem',
            color: 'var(--accent-cyan)',
            textDecoration: 'none',
            padding: '0.5rem 0.75rem',
            borderRadius: 'var(--radius-sm)',
            backgroundColor: 'var(--bg-tertiary)',
            transition: 'background-color var(--transition-fast)',
          }}
        >
          <span>OpenAPI Docs</span>
          <ExternalLink size={12} />
        </a>
      </div>
    </aside>
  );
};

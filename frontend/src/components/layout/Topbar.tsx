import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Menu,
  RefreshCw,
  FileCode2,
} from 'lucide-react';
import { Button } from '../common/Button';
import { apiService, API_BASE_URL } from '../../services/api';

export interface TopbarProps {
  onToggleSidebar?: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': {
    title: 'Executive Intelligence Command Center',
    subtitle: 'Cross-platform stream synthesis, engagement depth, and sentiment polarity index',
  },
  '/timeline': {
    title: 'Chronological Timeline & Trend Radar',
    subtitle: 'Multi-interval velocity curves, emerging narrative spikes, and cross-platform comparisons',
  },
  '/posts': {
    title: 'Social Stream Evidence Explorer',
    subtitle: 'Full-text search, multi-metric filtering, and granular post intelligence',
  },
  '/network': {
    title: 'Entity Co-occurrence Network Graph',
    subtitle: 'Relational mapping between hashtags and user mentions across social streams',
  },
  '/health': {
    title: 'System Health & Pipeline Diagnostics',
    subtitle: 'Real-time FastAPI gateway, PostgreSQL, and adapter status probes',
  },
};

export const Topbar: React.FC<TopbarProps> = ({
  onToggleSidebar,
  onRefresh,
  isRefreshing = false,
}) => {
  const location = useLocation();
  const currentRouteInfo = routeTitles[location.pathname] || {
    title: 'InsightX Intelligence Platform',
    subtitle: 'Smart India Hackathon 2026 Problem Statement 26152',
  };

  const [isLive, setIsLive] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    const checkLive = async () => {
      try {
        await apiService.getHealth();
        if (isMounted) setIsLive(true);
      } catch {
        if (isMounted) setIsLive(false);
      }
    };
    checkLive();
    const interval = setInterval(checkLive, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Mobile Hamburger Button */}
        <button
          onClick={onToggleSidebar}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            padding: '0.4rem',
            display: 'none',
          }}
          className="mobile-menu-btn"
          aria-label="Toggle navigation menu"
        >
          <Menu size={22} />
        </button>

        <div>
          <h2
            style={{
              fontSize: '1.05rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              lineHeight: 1.2,
            }}
          >
            {currentRouteInfo.title}
          </h2>
          <p
            style={{
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              display: 'none',
            }}
            className="topbar-subtitle"
          >
            {currentRouteInfo.subtitle}
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        {/* Live Backend Connection Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            fontSize: '0.78rem',
            padding: '0.35rem 0.75rem',
            borderRadius: 'var(--radius-full)',
            backgroundColor: isLive
              ? 'rgba(0, 230, 118, 0.1)'
              : isLive === false
              ? 'rgba(255, 82, 82, 0.1)'
              : 'var(--bg-tertiary)',
            color: isLive
              ? 'var(--sentiment-pos)'
              : isLive === false
              ? 'var(--sentiment-neg)'
              : 'var(--text-muted)',
            border: `1px solid ${
              isLive
                ? 'rgba(0, 230, 118, 0.25)'
                : isLive === false
                ? 'rgba(255, 82, 82, 0.25)'
                : 'var(--border-subtle)'
            }`,
            fontWeight: 600,
          }}
          title={`Base URL: ${API_BASE_URL}`}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isLive
                ? 'var(--sentiment-pos)'
                : isLive === false
                ? 'var(--sentiment-neg)'
                : 'var(--text-muted)',
              boxShadow: isLive ? '0 0 6px var(--sentiment-pos)' : 'none',
            }}
          />
          <span>{isLive ? 'BACKEND ONLINE' : isLive === false ? 'OFFLINE' : 'CHECKING...'}</span>
        </div>

        {/* OpenAPI Interactive Docs Link */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.4rem 0.75rem',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.8rem',
            fontWeight: 500,
            textDecoration: 'none',
            transition: 'color var(--transition-fast)',
          }}
          className="api-docs-link"
        >
          <FileCode2 size={14} color="var(--accent-cyan)" />
          <span>Swagger Docs</span>
        </a>

        {/* Global Refresh Action */}
        {onRefresh && (
          <Button
            size="sm"
            variant="secondary"
            onClick={onRefresh}
            loading={isRefreshing}
            icon={<RefreshCw size={14} />}
            title="Refresh dashboard intelligence"
          >
            Refresh
          </Button>
        )}
      </div>
    </header>
  );
};

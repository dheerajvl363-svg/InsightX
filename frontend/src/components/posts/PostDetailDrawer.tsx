import React, { useState, useEffect } from 'react';
import {
  X,
  ExternalLink,
  Copy,
  Check,
  Heart,
  MessageCircle,
  Share2,
  Eye,
  Calendar,
  Clock,
  Globe,
  Code2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { PostSummary } from '../../types/api';
import { Badge, Button } from '../common';

interface PostDetailDrawerProps {
  post: PostSummary | null;
  onClose: () => void;
}

export const PostDetailDrawer: React.FC<PostDetailDrawerProps> = ({ post, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!post) return null;

  const handleCopyText = async () => {
    if (post.text) {
      await navigator.clipboard.writeText(post.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getPlatformVariant = (platform: string) => {
    const key = platform.toLowerCase();
    if (key === 'x') return 'x' as const;
    if (key === 'reddit') return 'reddit' as const;
    if (key === 'telegram') return 'telegram' as const;
    if (key === 'youtube') return 'youtube' as const;
    return 'cyan' as const;
  };

  const platformVariant = getPlatformVariant(post.platform);
  const authorName = post.author_display_name || post.author_username || 'Anonymous';
  const authorHandle = post.author_username ? `@${post.author_username}` : '';
  const authorInitials = authorName.substring(0, 2).toUpperCase();

  const likes = post.metrics?.likes ?? 0;
  const comments = post.metrics?.comments ?? 0;
  const shares = post.metrics?.shares ?? 0;
  const views = post.metrics?.views ?? 0;

  const formattedPostedAt = new Date(post.posted_at).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short',
  });

  const formattedCollectedAt = post.collected_at
    ? new Date(post.collected_at).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short',
      })
    : null;

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
          zIndex: 'var(--z-drawer)',
          animation: 'fadeIn 0.2s ease-out',
        }}
      />

      {/* Drawer Container */}
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
          overflowY: 'auto',
          animation: 'fadeIn 0.25s ease-out',
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            backgroundColor: 'var(--bg-secondary)',
            backdropFilter: 'blur(10px)',
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Badge variant={platformVariant} size="md">
              {post.platform}
            </Badge>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              ID: #{post.id}
            </span>
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
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Close Drawer (Esc)"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body Content */}
        <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Author Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1rem',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
              <div
                style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: `var(--platform-${platformVariant === 'x' ? 'x' : platformVariant === 'reddit' ? 'reddit' : platformVariant === 'telegram' ? 'telegram' : 'youtube'}-bg, var(--accent-cyan-bg))`,
                  color: `var(--platform-${platformVariant === 'x' ? 'x' : platformVariant === 'reddit' ? 'reddit' : platformVariant === 'telegram' ? 'telegram' : 'youtube'}, var(--accent-cyan))`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '1rem',
                }}
              >
                {authorInitials}
              </div>
              <div>
                <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {authorName}
                </div>
                {authorHandle && (
                  <div style={{ fontSize: '0.825rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {authorHandle}
                  </div>
                )}
              </div>
            </div>

            {post.url && (
              <a
                href={post.url}
                target="_blank"
                rel="noreferrer noopener"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.825rem',
                  color: 'var(--accent-cyan)',
                  textDecoration: 'none',
                  padding: '0.4rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--accent-cyan-bg)',
                  border: '1px solid rgba(0, 210, 255, 0.25)',
                }}
              >
                <span>Original Post</span>
                <ExternalLink size={13} />
              </a>
            )}
          </div>

          {/* Full Post Text */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Post Content
              </span>
              <Button
                size="sm"
                variant="ghost"
                icon={copied ? <Check size={14} color="var(--sentiment-pos)" /> : <Copy size={14} />}
                onClick={handleCopyText}
              >
                {copied ? 'Copied' : 'Copy Text'}
              </Button>
            </div>
            <div
              style={{
                padding: '1.25rem',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.95rem',
                lineHeight: 1.6,
                color: 'var(--text-primary)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {post.text || <span style={{ color: 'var(--text-muted)' }}>No text content recorded.</span>}
            </div>
          </div>

          {/* Engagement Metrics Telemetry */}
          <div>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '0.65rem' }}>
              Engagement Telemetry
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--sentiment-neg-bg)', color: 'var(--sentiment-neg)' }}>
                  <Heart size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Likes</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {likes.toLocaleString()}
                  </div>
                </div>
              </div>

              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-cyan-bg)', color: 'var(--accent-cyan)' }}>
                  <MessageCircle size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Comments</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {comments.toLocaleString()}
                  </div>
                </div>
              </div>

              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--sentiment-pos-bg)', color: 'var(--sentiment-pos)' }}>
                  <Share2 size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Shares</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {shares.toLocaleString()}
                  </div>
                </div>
              </div>

              <div
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: 'var(--bg-surface)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <div style={{ padding: '0.5rem', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--accent-purple-bg)', color: 'var(--accent-purple)' }}>
                  <Eye size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Views</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                    {views > 0 ? views.toLocaleString() : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Temporal & Ingestion Details */}
          <div>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '0.65rem' }}>
              Pipeline Ingestion Specs
            </span>
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                padding: '0.85rem 1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                fontSize: '0.85rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                  <Calendar size={15} /> Published Time
                </span>
                <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                  {formattedPostedAt}
                </span>
              </div>

              {formattedCollectedAt && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                    <Clock size={15} /> Ingestion Time
                  </span>
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                    {formattedCollectedAt}
                  </span>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                  <Globe size={15} /> Language
                </span>
                <Badge variant="neutral" size="sm">
                  {post.language ? post.language.toUpperCase() : 'UNKNOWN'}
                </Badge>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>External ID</span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                  {post.external_post_id}
                </span>
              </div>
            </div>
          </div>

          {/* Raw JSON Inspector Accordion */}
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              overflow: 'hidden',
            }}
          >
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              style={{
                width: '100%',
                padding: '0.85rem 1rem',
                backgroundColor: 'transparent',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Code2 size={16} color="var(--accent-cyan)" />
                Raw Telemetry Payload JSON
              </span>
              {showRawJson ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showRawJson && (
              <pre
                style={{
                  padding: '1rem',
                  margin: 0,
                  backgroundColor: 'var(--bg-primary)',
                  color: 'var(--accent-cyan)',
                  fontSize: '0.78rem',
                  fontFamily: 'var(--font-mono)',
                  overflowX: 'auto',
                  borderTop: '1px solid var(--border-subtle)',
                  maxHeight: '260px',
                }}
              >
                {JSON.stringify(post, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

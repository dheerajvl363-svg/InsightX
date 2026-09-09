import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  Plus,
  Trash2,
  Send,
  Database,
  Bot,
} from 'lucide-react';
import { Badge, Button, ErrorBanner } from '../common';
import { api } from '../../services/api';
import type {
  DemoAnalysisResponse,
  DemoAnalyzePostsRequest,
  DemoContextMode,
} from '../../types/api';

interface AnalyzePostModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (response: DemoAnalysisResponse) => void;
}

interface PostFormState {
  text: string;
  platform: string;
  author_handle: string;
  url: string;
  likes: number;
  reposts: number;
  replies: number;
  views: number;
}

const INITIAL_POST: PostFormState = {
  text: '',
  platform: 'X',
  author_handle: '@researcher_sec',
  url: '',
  likes: 120,
  reposts: 35,
  replies: 18,
  views: 4500,
};

const PRESETS = [
  {
    id: 'cloud_outage',
    name: 'Cloud Outage Surge',
    badge: 'DEMO / SAMPLE',
    description: 'Major cloud provider network disruption and failover telemetry.',
    posts: [
      {
        text: 'CRITICAL: Multiple availability zones experiencing severe DNS and network packet loss in us-east region. Investigation ongoing. #CloudOutage #Downtime',
        platform: 'X',
        author_handle: '@cloud_watchdog',
        url: 'https://x.com/cloud_watchdog/status/9887711',
        likes: 1420,
        reposts: 680,
        replies: 230,
        views: 89000,
      },
      {
        text: 'API gateway error rates elevated to 42%. Failover clusters taking over traffic. Expect latency spikes across downstream services.',
        platform: 'X',
        author_handle: '@infra_ops',
        url: 'https://x.com/infra_ops/status/9887712',
        likes: 540,
        reposts: 180,
        replies: 95,
        views: 34000,
      },
    ],
  },
  {
    id: 'cybersecurity',
    name: 'Cybersecurity Alert',
    badge: 'DEMO / SAMPLE',
    description: 'Zero-day vulnerability advisory and mitigation recommendations.',
    posts: [
      {
        text: 'Urgent Security Advisory: High-severity zero-day exploit detected in enterprise auth libraries. Immediate patching required. CVE-2026-9921 #CyberSecurity #InfoSec',
        platform: 'X',
        author_handle: '@threat_intel',
        url: 'https://x.com/threat_intel/status/8877102',
        likes: 2150,
        reposts: 1240,
        replies: 310,
        views: 142000,
      },
    ],
  },
  {
    id: 'digital_infra',
    name: 'Digital Public Infrastructure',
    badge: 'DEMO / SAMPLE',
    description: 'Public digital infrastructure adoption and transaction milestone.',
    posts: [
      {
        text: 'Remarkable milestone: Digital public payment infrastructure records over 15 billion monthly transactions. Reliability metrics remain at 99.98%. #DPI #FinTech',
        platform: 'X',
        author_handle: '@dpi_monitor',
        url: 'https://x.com/dpi_monitor/status/7766551',
        likes: 890,
        reposts: 310,
        replies: 74,
        views: 45000,
      },
    ],
  },
];

export const AnalyzePostModal: React.FC<AnalyzePostModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [posts, setPosts] = useState<PostFormState[]>([{ ...INITIAL_POST }]);
  const [contextMode, setContextMode] = useState<DemoContextMode>('sample_stream');
  const [includeAi, setIncludeAi] = useState<boolean>(true);
  const [persistToDb, setPersistToDb] = useState<boolean>(true);
  const [promptInstructions, setPromptInstructions] = useState<string>('');
  const [activeTab, setActiveTab] = useState<number>(0);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen) return null;

  const handleAddPost = () => {
    if (posts.length >= 50) return;
    setPosts((prev) => [
      ...prev,
      {
        text: '',
        platform: 'X',
        author_handle: `@author_${prev.length + 1}`,
        url: '',
        likes: 0,
        reposts: 0,
        replies: 0,
        views: 0,
      },
    ]);
    setActiveTab(posts.length);
  };

  const handleRemovePost = (idx: number) => {
    if (posts.length <= 1) return;
    setPosts((prev) => prev.filter((_, i) => i !== idx));
    setActiveTab((prev) => (prev >= idx ? Math.max(0, prev - 1) : prev));
  };

  const handleUpdateCurrentPost = (field: keyof PostFormState, value: unknown) => {
    setPosts((prev) => {
      const next = [...prev];
      next[activeTab] = {
        ...next[activeTab],
        [field]: value,
      };
      return next;
    });
  };

  const handleLoadPreset = (presetId: string) => {
    const found = PRESETS.find((p) => p.id === presetId);
    if (!found) return;
    setPosts(found.posts.map((p) => ({ ...p })));
    setActiveTab(0);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate posts
    for (let i = 0; i < posts.length; i++) {
      if (!posts[i].text.trim()) {
        setError(`Post #${i + 1} content cannot be empty.`);
        setActiveTab(i);
        return;
      }
      if (posts[i].text.trim().length > 2000) {
        setError(`Post #${i + 1} exceeds 2000 character limit.`);
        setActiveTab(i);
        return;
      }
    }

    setIsSubmitting(true);

    try {
      const payload: DemoAnalyzePostsRequest = {
        posts: posts.map((p) => ({
          text: p.text.trim(),
          platform: p.platform || 'X',
          author_handle: p.author_handle.trim() || undefined,
          url: p.url.trim() || undefined,
          likes: Number(p.likes) || 0,
          reposts: Number(p.reposts) || 0,
          replies: Number(p.replies) || 0,
          views: Number(p.views) || 0,
        })),
        context_mode: contextMode,
        persist_to_db: persistToDb,
        include_ai: includeAi,
        prompt_instructions: promptInstructions.trim() || undefined,
      };

      const result = await api.analyzeDemoPosts(payload);
      onSuccess(result);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to analyze demo posts.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentPost = posts[activeTab] || posts[0];

  return (
    <div style={{ position: 'relative', zIndex: 'var(--z-modal)' }}>
      {/* Backdrop */}
      <div
        onClick={() => {
          if (!isSubmitting) onClose();
        }}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(5, 8, 16, 0.78)',
          backdropFilter: 'blur(5px)',
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
          width: '92%',
          maxWidth: '780px',
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--accent-purple-bg)',
                color: 'var(--accent-purple)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Send size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Analyze Social Posts
                </h2>
                <Badge variant="cyan" size="sm">
                  Phase 9 Demo
                </Badge>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '2px' }}>
                Supply 1 to 50 posts to generate deterministic analytics, evidence provenance, and AI insights.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              padding: '0.4rem',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', flex: 1 }}>
          <div style={{ padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            {error && <ErrorBanner message={error} />}

            {/* Quick Presets Bar */}
            <div
              style={{
                padding: '0.85rem 1rem',
                backgroundColor: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '0.6rem',
                }}
              >
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Quick Presets (Deterministic SIH Scenarios)
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>
                  Honest sample data (not fabricated live telemetry)
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handleLoadPreset(preset.id)}
                    disabled={isSubmitting}
                    style={{
                      padding: '0.4rem 0.75rem',
                      backgroundColor: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <Sparkles size={13} style={{ color: 'var(--accent-purple)' }} />
                    <span>{preset.name}</span>
                    <span
                      style={{
                        fontSize: '0.65rem',
                        padding: '1px 5px',
                        borderRadius: '3px',
                        backgroundColor: 'rgba(56, 189, 248, 0.15)',
                        color: 'var(--accent-cyan)',
                      }}
                    >
                      {preset.posts.length} post{preset.posts.length > 1 ? 's' : ''}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Post Tabs Selection */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', overflowX: 'auto', paddingBottom: '2px' }}>
                {posts.map((_, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActiveTab(idx)}
                    style={{
                      padding: '0.35rem 0.7rem',
                      borderRadius: 'var(--radius-sm)',
                      border: idx === activeTab ? '1px solid var(--accent-purple)' : '1px solid var(--border-subtle)',
                      backgroundColor: idx === activeTab ? 'var(--accent-purple-bg)' : 'var(--bg-surface)',
                      color: idx === activeTab ? 'var(--accent-purple)' : 'var(--text-secondary)',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    Post #{idx + 1}
                  </button>
                ))}
                {posts.length < 50 && (
                  <button
                    type="button"
                    onClick={handleAddPost}
                    disabled={isSubmitting}
                    style={{
                      padding: '0.35rem 0.6rem',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px dashed var(--border-subtle)',
                      backgroundColor: 'transparent',
                      color: 'var(--text-tertiary)',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    <Plus size={14} />
                    <span>Add</span>
                  </button>
                )}
              </div>

              {posts.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemovePost(activeTab)}
                  disabled={isSubmitting}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--accent-red, #f43f5e)',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                  }}
                >
                  <Trash2 size={13} />
                  <span>Remove Post #{activeTab + 1}</span>
                </button>
              )}
            </div>

            {/* Post Content Input Area */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '1rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                  <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Post Text / Caption <span style={{ color: 'var(--accent-red, #f43f5e)' }}>*</span>
                  </label>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      color: currentPost.text.length > 2000 ? 'var(--accent-red)' : 'var(--text-tertiary)',
                    }}
                  >
                    {currentPost.text.length} / 2000 chars
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={currentPost.text}
                  onChange={(e) => handleUpdateCurrentPost('text', e.target.value)}
                  placeholder="Paste or write the social post content (e.g. outage report, user sentiment, announcement)..."
                  disabled={isSubmitting}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem',
                    backgroundColor: 'var(--bg-primary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontFamily: 'inherit',
                    resize: 'vertical',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Metadata Fields (Platform, Handle, URL) */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                    Platform
                  </label>
                  <select
                    value={currentPost.platform}
                    onChange={(e) => handleUpdateCurrentPost('platform', e.target.value)}
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      outline: 'none',
                    }}
                  >
                    <option value="X">X (Twitter)</option>
                    <option value="Reddit">Reddit</option>
                    <option value="Telegram">Telegram</option>
                    <option value="YouTube">YouTube</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                    Author Handle
                  </label>
                  <input
                    type="text"
                    value={currentPost.author_handle}
                    onChange={(e) => handleUpdateCurrentPost('author_handle', e.target.value)}
                    placeholder="@username"
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      outline: 'none',
                    }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                    Post Link / URL (Optional)
                  </label>
                  <input
                    type="text"
                    value={currentPost.url}
                    onChange={(e) => handleUpdateCurrentPost('url', e.target.value)}
                    placeholder="https://x.com/..."
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              {/* Engagement Metrics Inputs */}
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                  Engagement Metrics Snapshot
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '2px' }}>Likes</span>
                    <input
                      type="number"
                      min={0}
                      value={currentPost.likes}
                      onChange={(e) => handleUpdateCurrentPost('likes', parseInt(e.target.value) || 0)}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        padding: '0.45rem',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-primary)',
                        fontSize: '0.8rem',
                      }}
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '2px' }}>Reposts</span>
                    <input
                      type="number"
                      min={0}
                      value={currentPost.reposts}
                      onChange={(e) => handleUpdateCurrentPost('reposts', parseInt(e.target.value) || 0)}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        padding: '0.45rem',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-primary)',
                        fontSize: '0.8rem',
                      }}
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '2px' }}>Replies</span>
                    <input
                      type="number"
                      min={0}
                      value={currentPost.replies}
                      onChange={(e) => handleUpdateCurrentPost('replies', parseInt(e.target.value) || 0)}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        padding: '0.45rem',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-primary)',
                        fontSize: '0.8rem',
                      }}
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', display: 'block', marginBottom: '2px' }}>Views</span>
                    <input
                      type="number"
                      min={0}
                      value={currentPost.views}
                      onChange={(e) => handleUpdateCurrentPost('views', parseInt(e.target.value) || 0)}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        padding: '0.45rem',
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--text-primary)',
                        fontSize: '0.8rem',
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Pipeline Configuration Options */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
                padding: '1rem',
                backgroundColor: 'rgba(15, 23, 42, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Analysis Pipeline Configuration
              </span>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                {/* Context Mode */}
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                    Context Baseline Mode
                  </label>
                  <select
                    value={contextMode}
                    onChange={(e) => setContextMode(e.target.value as DemoContextMode)}
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                    }}
                  >
                    <option value="sample_stream">Sample Stream (Mock Baseline)</option>
                    <option value="database">Database Context (Recent DB)</option>
                    <option value="none">None (User Posts Only)</option>
                  </select>
                </div>

                {/* AI Qualitative Interpretation */}
                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={includeAi}
                      onChange={(e) => setIncludeAi(e.target.checked)}
                      disabled={isSubmitting}
                      style={{ cursor: 'pointer' }}
                    />
                    <Bot size={15} style={{ color: 'var(--accent-purple)' }} />
                    <span>Include Grounded AI Interpretation</span>
                  </label>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginLeft: '1.4rem' }}>
                    Evidence-grounded narrative synthesis (failure-safe)
                  </span>
                </div>

                {/* Persist to Database */}
                <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <label
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={persistToDb}
                      onChange={(e) => setPersistToDb(e.target.checked)}
                      disabled={isSubmitting}
                      style={{ cursor: 'pointer' }}
                    />
                    <Database size={15} style={{ color: 'var(--accent-cyan)' }} />
                    <span>Persist User Posts to Database</span>
                  </label>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', marginLeft: '1.4rem' }}>
                    Ingests through IngestionService with deduplication
                  </span>
                </div>
              </div>

              {includeAi && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                    Custom Focus Instructions for AI (Optional)
                  </label>
                  <input
                    type="text"
                    maxLength={500}
                    value={promptInstructions}
                    onChange={(e) => setPromptInstructions(e.target.value)}
                    placeholder="e.g. Focus on operational mitigation and customer impact..."
                    disabled={isSubmitting}
                    style={{
                      width: '100%',
                      padding: '0.45rem 0.65rem',
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Footer Controls */}
          <div
            style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'var(--bg-surface)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Badge variant="neutral" size="sm">
                {posts.length} Post{posts.length > 1 ? 's' : ''} Ready
              </Badge>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                Provenance: <strong style={{ color: 'var(--accent-cyan)' }}>user_supplied</strong>
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                type="submit"
                disabled={isSubmitting}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  minWidth: '160px',
                  justifyContent: 'center',
                }}
              >
                {isSubmitting ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                    <span>Analyzing Pipeline...</span>
                  </>
                ) : (
                  <>
                    <Send size={14} />
                    <span>Run Demo Analysis</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

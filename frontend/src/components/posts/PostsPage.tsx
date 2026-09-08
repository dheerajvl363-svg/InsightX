import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  LayoutGrid,
  List,
  Heart,
  MessageCircle,
  Share2,
  Eye,
  RotateCcw,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ArrowUpDown,
  Filter,
} from 'lucide-react';
import { Card, Badge, Button, Skeleton, ErrorBanner } from '../common';
import { usePosts } from '../../hooks/usePosts';
import type { PostQueryParams, PostSummary } from '../../types/api';
import { PostDetailDrawer } from './PostDetailDrawer';

export const PostsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Read initial params from URL if present
  const initialSearch = searchParams.get('search') || '';
  const initialPlatform = searchParams.get('platform') || 'all';
  const initialAuthor = searchParams.get('author') || '';

  // Filter & Search state
  const [searchQuery, setSearchQuery] = useState<string>(initialSearch);
  const [debouncedQuery, setDebouncedQuery] = useState<string>(initialSearch);
  const [selectedPlatform, setSelectedPlatform] = useState<string>(initialPlatform);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('all');
  const [authorFilter, setAuthorFilter] = useState<string>(initialAuthor);
  const [minLikesFilter, setMinLikesFilter] = useState<string>('');
  const [sortOption, setSortOption] = useState<string>('posted_at_desc');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(!!initialAuthor);

  // Sync state if URL searchParams change externally (e.g. user navigation)
  useEffect(() => {
    const s = searchParams.get('search');
    const p = searchParams.get('platform');
    const a = searchParams.get('author');
    if (s !== null && s !== searchQuery) {
      setSearchQuery(s);
      setDebouncedQuery(s);
    }
    if (p !== null && p !== selectedPlatform) {
      setSelectedPlatform(p);
    }
    if (a !== null && a !== authorFilter) {
      setAuthorFilter(a);
      setShowAdvancedFilters(true);
    }
  }, [searchParams]);

  // View & Pagination state
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [page, setPage] = useState<number>(1);
  const [selectedPost, setSelectedPost] = useState<PostSummary | null>(null);
  const limit = 24;

  // Debounce search input by 400ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1); // Reset to page 1 on new search
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Construct query parameters matching backend /posts contract
  const queryParams = useMemo<PostQueryParams>(() => {
    const params: PostQueryParams = {
      limit,
      offset: (page - 1) * limit,
    };

    if (debouncedQuery.trim()) {
      params.search = debouncedQuery.trim();
    }

    if (selectedPlatform !== 'all') {
      params.platform = selectedPlatform;
    }

    if (selectedLanguage !== 'all') {
      params.language = selectedLanguage;
    }

    if (authorFilter.trim()) {
      params.author = authorFilter.trim();
    }

    if (minLikesFilter.trim() && !isNaN(Number(minLikesFilter))) {
      params.min_likes = Number(minLikesFilter);
    }

    // Map sort options
    const [field, order] = sortOption.split('_');
    if (field && order) {
      params.sort_by = field;
      params.order = order as 'asc' | 'desc';
    }

    return params;
  }, [
    debouncedQuery,
    selectedPlatform,
    selectedLanguage,
    authorFilter,
    minLikesFilter,
    sortOption,
    page,
  ]);

  const { data, loading, error, refetch } = usePosts(queryParams);

  const totalPosts = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalPosts / limit));

  const handleResetFilters = () => {
    setSearchQuery('');
    setDebouncedQuery('');
    setSelectedPlatform('all');
    setSelectedLanguage('all');
    setAuthorFilter('');
    setMinLikesFilter('');
    setSortOption('posted_at_desc');
    setPage(1);
    setSearchParams({});
  };

  const platforms = [
    { id: 'all', label: 'All Feeds' },
    { id: 'X', label: 'X (Twitter)', variant: 'x' as const },
    { id: 'Reddit', label: 'Reddit', variant: 'reddit' as const },
    { id: 'Telegram', label: 'Telegram', variant: 'telegram' as const },
    { id: 'YouTube', label: 'YouTube', variant: 'youtube' as const },
  ];

  const getPlatformVariant = (platform: string) => {
    const key = platform.toLowerCase();
    if (key === 'x') return 'x' as const;
    if (key === 'reddit') return 'reddit' as const;
    if (key === 'telegram') return 'telegram' as const;
    if (key === 'youtube') return 'youtube' as const;
    return 'cyan' as const;
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <h1
          style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            marginBottom: '0.35rem',
          }}
        >
          Social Stream Evidence Explorer
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem' }}>
          Real-time query, filter, and deep inspection interface backed directly by FastAPI database records.
        </p>
      </div>

      {/* Filter & Search Toolbar */}
      <Card style={{ marginBottom: '1.5rem', padding: '1.25rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Top Search & Primary Action Row */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                flex: 1,
                minWidth: '280px',
                backgroundColor: 'var(--bg-tertiary)',
                padding: '0.6rem 1rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <Search size={18} color="var(--text-muted)" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search keywords, #hashtags, @handles in post body..."
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-primary)',
                  outline: 'none',
                  width: '100%',
                  fontSize: '0.9rem',
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                  }}
                >
                  Clear
                </button>
              )}
            </div>

            {/* Sorting Dropdown */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <ArrowUpDown size={15} color="var(--text-muted)" />
              <select
                value={sortOption}
                onChange={(e) => {
                  setSortOption(e.target.value);
                  setPage(1);
                }}
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.6rem 0.85rem',
                  fontSize: '0.85rem',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="posted_at_desc">Most Recent</option>
                <option value="posted_at_asc">Oldest First</option>
                <option value="likes_desc">Highest Likes</option>
                <option value="comments_desc">Highest Comments</option>
                <option value="shares_desc">Highest Shares</option>
                <option value="views_desc">Highest Views</option>
              </select>
            </div>

            {/* Advanced Filters Toggle */}
            <Button
              variant={showAdvancedFilters ? 'primary' : 'secondary'}
              size="md"
              icon={<SlidersHorizontal size={14} />}
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
            >
              Filters
            </Button>

            {/* Reset Filters */}
            <Button
              variant="secondary"
              size="md"
              icon={<RotateCcw size={14} />}
              onClick={handleResetFilters}
            >
              Reset
            </Button>
          </div>

          {/* Platform Filter Chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500, marginRight: '0.25rem' }}>
              Network:
            </span>
            {platforms.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setSelectedPlatform(p.id);
                  setPage(1);
                }}
                style={{
                  backgroundColor: selectedPlatform === p.id ? 'var(--accent-cyan-bg)' : 'var(--bg-tertiary)',
                  color: selectedPlatform === p.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  border: `1px solid ${selectedPlatform === p.id ? 'rgba(0, 210, 255, 0.4)' : 'var(--border-subtle)'}`,
                  borderRadius: 'var(--radius-full)',
                  padding: '0.35rem 0.85rem',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Expandable Advanced Filters Drawer */}
          {showAdvancedFilters && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '0.85rem',
                paddingTop: '0.85rem',
                borderTop: '1px solid var(--border-subtle)',
                animation: 'fadeIn 0.2s ease-out',
              }}
            >
              {/* Author Username Filter */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Author Username
                </label>
                <input
                  type="text"
                  value={authorFilter}
                  onChange={(e) => {
                    setAuthorFilter(e.target.value);
                    setPage(1);
                  }}
                  placeholder="e.g. tech_lead"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.45rem 0.75rem',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>

              {/* Language Filter */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Language
                </label>
                <select
                  value={selectedLanguage}
                  onChange={(e) => {
                    setSelectedLanguage(e.target.value);
                    setPage(1);
                  }}
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.45rem 0.75rem',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <option value="all">All Languages</option>
                  <option value="en">English (en)</option>
                  <option value="es">Spanish (es)</option>
                  <option value="fr">French (fr)</option>
                  <option value="de">German (de)</option>
                  <option value="hi">Hindi (hi)</option>
                </select>
              </div>

              {/* Minimum Likes Threshold */}
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Min Likes
                </label>
                <input
                  type="number"
                  min="0"
                  value={minLikesFilter}
                  onChange={(e) => {
                    setMinLikesFilter(e.target.value);
                    setPage(1);
                  }}
                  placeholder="e.g. 50"
                  style={{
                    width: '100%',
                    backgroundColor: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.45rem 0.75rem',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Error Banner with Retry */}
      {error && (
        <div style={{ marginBottom: '1.5rem' }}>
          <ErrorBanner
            title="Failed to Load Posts"
            message={error}
            onRetry={refetch}
          />
        </div>
      )}

      {/* Results Header & View Toggle */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1.25rem',
          flexWrap: 'wrap',
          gap: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            {loading ? 'Querying records...' : `Found ${totalPosts.toLocaleString()} Post Evidence Records`}
          </span>
          <Badge variant={error ? 'negative' : 'cyan'} size="sm">
            /api/v1/posts
          </Badge>
        </div>

        {/* View Switcher Controls */}
        <div
          style={{
            display: 'flex',
            backgroundColor: 'var(--bg-tertiary)',
            padding: '0.2rem',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <button
            onClick={() => setViewMode('grid')}
            style={{
              background: viewMode === 'grid' ? 'var(--bg-surface)' : 'transparent',
              color: viewMode === 'grid' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              border: 'none',
              borderRadius: 'var(--radius-xs)',
              padding: '0.35rem 0.6rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
            title="Card Grid View"
          >
            <LayoutGrid size={15} />
            <span>Cards</span>
          </button>
          <button
            onClick={() => setViewMode('table')}
            style={{
              background: viewMode === 'table' ? 'var(--bg-surface)' : 'transparent',
              color: viewMode === 'table' ? 'var(--accent-cyan)' : 'var(--text-muted)',
              border: 'none',
              borderRadius: 'var(--radius-xs)',
              padding: '0.35rem 0.6rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
            title="Data Table View"
          >
            <List size={15} />
            <span>Table</span>
          </button>
        </div>
      </div>

      {/* Main Content Area: Grid vs Table */}
      {viewMode === 'grid' ? (
        /* Grid Cards View */
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '1.25rem',
            marginBottom: '2rem',
          }}
        >
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} style={{ minHeight: '220px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '1rem' }}>
                  <Skeleton width="34px" height="34px" borderRadius="50%" />
                  <div>
                    <Skeleton width="110px" height="14px" style={{ marginBottom: '0.4rem' }} />
                    <Skeleton width="75px" height="12px" />
                  </div>
                </div>
                <Skeleton width="100%" height="14px" style={{ marginBottom: '0.4rem' }} />
                <Skeleton width="90%" height="14px" style={{ marginBottom: '0.4rem' }} />
                <Skeleton width="70%" height="14px" style={{ marginBottom: '1rem' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Skeleton width="130px" height="18px" />
                  <Skeleton width="60px" height="18px" borderRadius="var(--radius-full)" />
                </div>
              </Card>
            ))
          ) : data?.items.length === 0 ? (
            <div
              style={{
                gridColumn: '1 / -1',
                padding: '4rem 2rem',
                textAlign: 'center',
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                border: '1px dashed var(--border-muted)',
              }}
            >
              <Filter size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem', opacity: 0.6 }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                No Posts Matching Criteria
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem', maxWidth: '380px', margin: '0 auto 1rem' }}>
                No records matched your search query or filters. Try adjusting keywords, clearing author filters, or switching platforms.
              </p>
              <Button size="sm" variant="secondary" icon={<RotateCcw size={14} />} onClick={handleResetFilters}>
                Clear All Filters
              </Button>
            </div>
          ) : (
            data?.items.map((post) => {
              const platformVariant = getPlatformVariant(post.platform);
              const authorName = post.author_display_name || post.author_username || 'Anonymous';
              const authorInitials = authorName.substring(0, 2).toUpperCase();

              const likes = post.metrics?.likes ?? 0;
              const comments = post.metrics?.comments ?? 0;
              const shares = post.metrics?.shares ?? 0;
              const views = post.metrics?.views ?? 0;

              return (
                <Card
                  key={post.id}
                  onClick={() => setSelectedPost(post)}
                  style={{
                    cursor: 'pointer',
                    transition: 'transform var(--transition-fast), border-color var(--transition-fast)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                  headerAction={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Badge variant={platformVariant} size="sm">
                        {post.platform}
                      </Badge>
                      {post.url && (
                        <a
                          href={post.url}
                          target="_blank"
                          rel="noreferrer noopener"
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            color: 'var(--text-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            padding: '0.2rem',
                          }}
                          title="Open original post"
                        >
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  }
                  footer={
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        color: 'var(--text-muted)',
                        fontSize: '0.78rem',
                      }}
                    >
                      <div style={{ display: 'flex', gap: '0.85rem' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Heart size={13} color="var(--sentiment-neg)" /> {likes.toLocaleString()}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <MessageCircle size={13} color="var(--accent-cyan)" /> {comments.toLocaleString()}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Share2 size={13} color="var(--sentiment-pos)" /> {shares.toLocaleString()}
                        </span>
                        {views > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <Eye size={13} /> {views > 1000 ? (views / 1000).toFixed(1) + 'k' : views}
                          </span>
                        )}
                      </div>

                      <span style={{ color: 'var(--accent-cyan)', fontSize: '0.75rem', fontWeight: 600 }}>
                        Inspect &rarr;
                      </span>
                    </div>
                  }
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.75rem' }}>
                    <div
                      style={{
                        width: '34px',
                        height: '34px',
                        borderRadius: '50%',
                        backgroundColor: `var(--platform-${platformVariant === 'x' ? 'x' : platformVariant === 'reddit' ? 'reddit' : platformVariant === 'telegram' ? 'telegram' : 'youtube'}-bg, var(--accent-cyan-bg))`,
                        color: `var(--platform-${platformVariant === 'x' ? 'x' : platformVariant === 'reddit' ? 'reddit' : platformVariant === 'telegram' ? 'telegram' : 'youtube'}, var(--accent-cyan))`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        fontSize: '0.85rem',
                        flexShrink: 0,
                      }}
                    >
                      {authorInitials}
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <div
                        style={{
                          fontSize: '0.9rem',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {authorName}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {new Date(post.posted_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </div>
                    </div>
                  </div>

                  <p
                    style={{
                      fontSize: '0.88rem',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.5,
                      marginBottom: '0.5rem',
                      wordBreak: 'break-word',
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {post.text || 'No text content recorded.'}
                  </p>
                </Card>
              );
            })
          )}
        </div>
      ) : (
        /* Data Table View */
        <Card style={{ marginBottom: '2rem', padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr
                  style={{
                    backgroundColor: 'var(--bg-tertiary)',
                    borderBottom: '1px solid var(--border-subtle)',
                    color: 'var(--text-muted)',
                    fontSize: '0.78rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  <th style={{ padding: '0.85rem 1rem' }}>Platform</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Author</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Post Text Preview</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Likes</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Comments</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Shares</th>
                  <th style={{ padding: '0.85rem 1rem' }}>Published</th>
                  <th style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '1rem' }}><Skeleton width="60px" height="20px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="90px" height="16px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="220px" height="16px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="40px" height="16px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="40px" height="16px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="40px" height="16px" /></td>
                      <td style={{ padding: '1rem' }}><Skeleton width="80px" height="16px" /></td>
                      <td style={{ padding: '1rem', textAlign: 'right' }}><Skeleton width="60px" height="24px" /></td>
                    </tr>
                  ))
                ) : data?.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No post records matched the current filters.
                    </td>
                  </tr>
                ) : (
                  data?.items.map((post) => {
                    const platformVariant = getPlatformVariant(post.platform);
                    const authorName = post.author_display_name || post.author_username || 'Anonymous';

                    return (
                      <tr
                        key={post.id}
                        onClick={() => setSelectedPost(post)}
                        style={{
                          borderBottom: '1px solid var(--border-subtle)',
                          cursor: 'pointer',
                          transition: 'background-color var(--transition-fast)',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-surface-hover)')}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                      >
                        <td style={{ padding: '0.85rem 1rem' }}>
                          <Badge variant={platformVariant} size="sm">
                            {post.platform}
                          </Badge>
                        </td>
                        <td style={{ padding: '0.85rem 1rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                          {authorName}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', color: 'var(--text-secondary)', maxWidth: '340px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {post.text || 'No text content'}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--sentiment-neg)' }}>
                          {(post.metrics?.likes ?? 0).toLocaleString()}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                          {(post.metrics?.comments ?? 0).toLocaleString()}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', fontFamily: 'var(--font-mono)', color: 'var(--sentiment-pos)' }}>
                          {(post.metrics?.shares ?? 0).toLocaleString()}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                          {new Date(post.posted_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '0.85rem 1rem', textAlign: 'right' }}>
                          <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); setSelectedPost(post); }}>
                            Inspect
                          </Button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination Controls Footer */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 0',
          borderTop: '1px solid var(--border-subtle)',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          {loading
            ? 'Updating page offsets...'
            : totalPosts > 0
            ? `Showing ${(page - 1) * limit + 1}–${Math.min(page * limit, totalPosts)} of ${totalPosts.toLocaleString()} records`
            : '0 records'}
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Button
            size="sm"
            variant="secondary"
            icon={<ChevronLeft size={14} />}
            disabled={page === 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>

          <span
            style={{
              padding: '0.35rem 0.75rem',
              fontSize: '0.825rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            Page {page} of {totalPages}
          </span>

          <Button
            size="sm"
            variant="secondary"
            icon={<ChevronRight size={14} />}
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </Button>
        </div>
      </div>

      {/* Post Detail Inspection Drawer */}
      <PostDetailDrawer
        post={selectedPost}
        onClose={() => setSelectedPost(null)}
      />
    </div>
  );
};

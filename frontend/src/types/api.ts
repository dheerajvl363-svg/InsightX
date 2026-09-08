/**
 * InsightX API Types
 * Strictly aligned with backend Phase 5 FastAPI schemas (backend/app/schemas/).
 */

// =============================================================================
// Common & Health Schemas (app/schemas/common.py)
// =============================================================================

export interface ErrorDetail {
  field?: string;
  message: string;
  type?: string;
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
  status_code?: number;
  errors?: ErrorDetail[];
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  services: Record<string, string>;
}

// =============================================================================
// Post & Engagement Schemas (app/schemas/analytics.py, app/schemas/post.py)
// =============================================================================

export interface PostMetricsSchema {
  likes: number;
  comments: number;
  shares: number;
  views: number;
}

export interface PostSummary {
  id: number;
  platform: string;
  external_post_id: string;
  text: string;
  author_username: string;
  author_display_name?: string | null;
  posted_at: string;
  collected_at?: string | null;
  url?: string | null;
  language?: string | null;
  metrics?: PostMetricsSchema | null;
  metadata?: Record<string, unknown>;
}

export interface PostListResponse {
  total: number;
  limit: number;
  offset: number;
  items: PostSummary[];
}

export interface CountResponse {
  total: number;
}

export interface EngagementSummary {
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_views: number;
  avg_likes: number;
  avg_comments: number;
  avg_shares: number;
  avg_views: number;
  engagement_rate: number;
}

// =============================================================================
// Platform Schemas (app/schemas/platforms.py, app/schemas/analytics.py)
// =============================================================================

export interface PlatformInfo {
  id: string;
  name: string;
  description: string;
  post_count: number;
  is_active: boolean;
  capabilities: string[];
}

export interface PlatformListResponse {
  platforms: PlatformInfo[];
}

export interface PlatformSummary {
  platform: string;
  post_count: number;
  percentage?: number;
  earliest_post?: string | null;
  latest_post?: string | null;
}

// =============================================================================
// Timeline Schemas (app/schemas/timeline.py)
// =============================================================================

export interface TimelineBucket {
  timestamp: string;
  count: number;
  platform_breakdown?: Record<string, number>;
}

export interface TimelineResponse {
  granularity: 'hour' | 'day' | 'week' | string;
  total_buckets: number;
  total_posts: number;
  buckets: TimelineBucket[];
}

// =============================================================================
// Sentiment Schemas (app/schemas/sentiment.py)
// =============================================================================

export interface SentimentProbabilities {
  positive: number;
  neutral: number;
  negative: number;
}

export interface SentimentResult {
  post_id?: number | null;
  external_post_id?: string | null;
  label: 'positive' | 'neutral' | 'negative';
  score: number;
  confidence: number;
  probabilities: SentimentProbabilities;
  model: string;
  analyzed_at: string;
  details?: Record<string, unknown>;
}

export interface BatchSentimentResult {
  total_analyzed: number;
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  average_score: number;
  results?: SentimentResult[];
}

// =============================================================================
// Topic Schemas (app/schemas/topic.py, app/schemas/analytics.py)
// =============================================================================

export interface ExtractedTopic {
  topic_id: string;
  label: string;
  keywords: string[];
  keyphrases: string[];
  post_count: number;
  post_ids?: number[];
  external_post_ids?: string[];
  confidence: number;
}

export interface BatchTopicResult {
  total_posts_analyzed: number;
  total_topics_found: number;
  topics: ExtractedTopic[];
  unclustered_posts_count: number;
  model: string;
  analyzed_at: string;
}

export interface TopicAnalyticsSummary {
  topic_name: string;
  post_count: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_views: number;
  avg_likes: number;
  avg_comments: number;
  avg_shares: number;
  avg_views: number;
  earliest_post?: string | null;
  latest_post?: string | null;
}

export interface TopicListResponse {
  total: number;
  limit: number;
  offset: number;
  items: TopicAnalyticsSummary[];
}

// =============================================================================
// Trend Schemas (app/schemas/trend.py)
// =============================================================================

export interface TimeWindow {
  start: string;
  end: string;
}

export interface TopicTrendResult {
  topic_id: string;
  topic_label: string;
  current_volume: number;
  baseline_volume: number;
  growth_rate: number;
  direction: 'emerging' | 'spiking' | 'growing' | 'stable' | 'declining';
  trend_score: number;
  is_emerging: boolean;
  is_spiking: boolean;
  post_ids?: number[];
  external_post_ids?: string[];
  current_window?: TimeWindow;
  baseline_window?: TimeWindow | null;
  details?: Record<string, unknown>;
}

export interface BatchTrendResult {
  total_topics_evaluated: number;
  emerging_topics_count: number;
  spiking_topics_count: number;
  growing_topics_count: number;
  trends: TopicTrendResult[];
  model: string;
  analyzed_at: string;
}

// =============================================================================
// Network & Graph Schemas (app/schemas/network.py)
// =============================================================================

export interface NetworkNode {
  id: string;
  label: string;
  node_type: 'author' | 'domain' | 'hashtag' | 'platform' | string;
  degree: number;
  influence_score: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  relation_type: string;
}

export interface BatchNetworkResult {
  total_nodes: number;
  total_edges: number;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  top_influencers?: NetworkNode[];
  top_domains?: Array<Record<string, unknown>>;
  analyzed_at: string;
}

export interface PlatformComparisonItem {
  platform: string;
  post_count: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  total_views: number;
  avg_engagement: number;
  sentiment_breakdown: Record<string, number>;
}

export interface PlatformComparisonResponse {
  total_platforms: number;
  platforms: PlatformComparisonItem[];
  generated_at: string;
}

// =============================================================================
// Consolidated Dashboard Overview (app/schemas/dashboard.py)
// =============================================================================

export interface DashboardOverviewResponse {
  total_posts: number;
  engagement_summary?: EngagementSummary | null;
  platforms: PlatformSummary[];
  sentiment?: BatchSentimentResult | null;
  topics?: BatchTopicResult | null;
  trends?: BatchTrendResult | null;
  network?: BatchNetworkResult | null;
  generated_at: string;
}

// =============================================================================
// Query Parameters
// =============================================================================

export interface PostQueryParams {
  platform?: string;
  language?: string;
  search?: string;
  keyword?: string; // backwards compatibility
  author?: string;
  sentiment?: string;
  start_date?: string;
  end_date?: string;
  min_likes?: number;
  min_comments?: number;
  min_shares?: number;
  min_views?: number;
  sort_by?: 'posted_at' | 'likes' | 'comments' | 'shares' | 'views' | string;
  order?: 'asc' | 'desc' | string;
  limit?: number;
  offset?: number;
}

export interface AnalyticsQueryParams {
  platform?: string;
  language?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

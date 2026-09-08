/**
 * InsightX Centralized API Client
 * Configured with VITE_API_BASE_URL (defaults to http://localhost:8000/api/v1).
 */
import type {
  AnalyticsQueryParams,
  BatchInsightResult,
  BatchNetworkResult,
  BatchSentimentResult,
  BatchTrendResult,
  DashboardOverviewResponse,
  ErrorResponse,
  HealthResponse,
  InsightExplanation,
  InsightQueryParams,
  IntelligenceAnalyzeRequest,
  PlatformComparisonResponse,
  PlatformInfo,
  PostListResponse,
  PostQueryParams,
  PostSummary,
  TimelineResponse,
  TopicListResponse,
} from '../types/api';

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  public statusCode: number;
  public errorResponse?: ErrorResponse;

  constructor(message: string, statusCode: number, errorResponse?: ErrorResponse) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorResponse = errorResponse;
  }
}

function buildQueryString(params: Record<string, unknown> = {}): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: ErrorResponse | undefined;
      try {
        errorData = await response.json();
      } catch {
        // Response was not valid JSON
      }

      const message =
        errorData?.detail ||
        (errorData?.errors && errorData.errors.length > 0
          ? errorData.errors.map((e) => e.message).join(', ')
          : `API request failed with status ${response.status}`);

      throw new ApiError(message, response.status, errorData);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error occurred',
      0
    );
  }
}

export const apiService = {
  // System Health
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health');
  },

  async getRootHealth(): Promise<{ status: string }> {
    const rootUrl = API_BASE_URL.replace(/\/api\/v1\/?$/, '');
    const res = await fetch(`${rootUrl}/health`);
    if (!res.ok) throw new ApiError('Root health probe failed', res.status);
    return res.json();
  },

  // Executive Overview Dashboard (GET /api/v1/analytics/overview)
  async getOverview(params: AnalyticsQueryParams = {}): Promise<DashboardOverviewResponse> {
    return request<DashboardOverviewResponse>(`/analytics/overview${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Posts Exploration (GET /api/v1/posts, GET /api/v1/posts/{id})
  async getPosts(params: PostQueryParams = {}): Promise<PostListResponse> {
    const { keyword, sentiment: _sentiment, ...rest } = params;
    const cleanParams: Record<string, unknown> = { ...rest };
    if (!cleanParams.search && keyword) {
      cleanParams.search = keyword;
    }
    return request<PostListResponse>(`/posts${buildQueryString(cleanParams)}`);
  },

  async getPostById(postId: number): Promise<PostSummary> {
    return request<PostSummary>(`/posts/${postId}`);
  },

  // Platforms (GET /api/v1/platforms)
  async getPlatforms(): Promise<PlatformInfo[]> {
    return request<PlatformInfo[]>('/platforms');
  },

  // Timeline (GET /api/v1/timeline)
  async getTimeline(
    granularity: 'hour' | 'day' | 'week' = 'day',
    platform?: string
  ): Promise<TimelineResponse> {
    const params: Record<string, unknown> = { granularity };
    if (platform) params.platform = platform;
    return request<TimelineResponse>(`/timeline${buildQueryString(params)}`);
  },

  // Sentiment Analytics (GET /api/v1/analytics/sentiment)
  async getSentiment(params: AnalyticsQueryParams = {}): Promise<BatchSentimentResult> {
    return request<BatchSentimentResult>(`/analytics/sentiment${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Topics Analytics (GET /api/v1/analytics/topics)
  async getTopics(params: AnalyticsQueryParams = {}): Promise<TopicListResponse> {
    return request<TopicListResponse>(`/analytics/topics${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Trends Analytics (GET /api/v1/analytics/trends)
  async getTrends(params: AnalyticsQueryParams = {}): Promise<BatchTrendResult> {
    return request<BatchTrendResult>(`/analytics/trends${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Network Graph (GET /api/v1/analytics/network)
  async getNetworkGraph(params: AnalyticsQueryParams = {}): Promise<BatchNetworkResult> {
    return request<BatchNetworkResult>(`/analytics/network${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Multi-Platform Comparison (GET /api/v1/analytics/platforms/compare)
  async getPlatformComparison(params: { start_date?: string; end_date?: string } = {}): Promise<PlatformComparisonResponse> {
    return request<PlatformComparisonResponse>(`/analytics/platforms/compare${buildQueryString(params as Record<string, unknown>)}`);
  },

  // Phase 7.2 Synthesized Intelligence API (GET /api/v1/insights, GET /api/v1/insights/{id}/explanation, POST /api/v1/analyze)
  async getInsights(params: InsightQueryParams = {}): Promise<BatchInsightResult> {
    const cleanParams: Record<string, unknown> = {};
    if (params.platform && params.platform !== 'all') cleanParams.platform = params.platform;
    if (params.min_confidence !== undefined) cleanParams.min_confidence = params.min_confidence;
    if (params.max_insights !== undefined) cleanParams.max_insights = params.max_insights;
    return request<BatchInsightResult>(`/insights${buildQueryString(cleanParams)}`);
  },

  async getInsightExplanation(insightId: string, platform?: string): Promise<InsightExplanation> {
    const params: Record<string, unknown> = {};
    if (platform && platform !== 'all') params.platform = platform;
    return request<InsightExplanation>(`/insights/${encodeURIComponent(insightId)}/explanation${buildQueryString(params)}`);
  },

  async analyzeIntelligence(payload: IntelligenceAnalyzeRequest): Promise<BatchInsightResult> {
    return request<BatchInsightResult>('/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { BatchTrendResult, AnalyticsQueryParams } from '../types/api';

export interface UseTrendsReturn {
  data: BatchTrendResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useTrends(
  params: AnalyticsQueryParams = {},
  autoFetch = true
): UseTrendsReturn {
  const [data, setData] = useState<BatchTrendResult | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getTrends(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch trend velocity analysis');
      }
    } finally {
      setLoading(false);
    }
  }, [
    params.platform,
    params.language,
    params.start_date,
    params.end_date,
    params.search,
    params.limit,
  ]);

  useEffect(() => {
    if (autoFetch) {
      fetchTrends();
    }
  }, [fetchTrends, autoFetch]);

  return { data, loading, error, refetch: fetchTrends };
}

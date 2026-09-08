import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { BatchInsightResult, InsightQueryParams } from '../types/api';

export interface UseInsightsReturn {
  data: BatchInsightResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useInsights(
  params: InsightQueryParams = {},
  autoFetch = true
): UseInsightsReturn {
  const [data, setData] = useState<BatchInsightResult | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getInsights(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to synthesize intelligence insights');
      }
    } finally {
      setLoading(false);
    }
  }, [params.platform, params.min_confidence, params.max_insights]);

  useEffect(() => {
    if (autoFetch) {
      fetchInsights();
    }
  }, [fetchInsights, autoFetch]);

  return { data, loading, error, refetch: fetchInsights };
}

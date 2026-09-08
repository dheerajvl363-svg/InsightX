import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { BatchSentimentResult, AnalyticsQueryParams } from '../types/api';

export interface UseSentimentReturn {
  data: BatchSentimentResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useSentiment(
  params: AnalyticsQueryParams = {},
  autoFetch = true
): UseSentimentReturn {
  const [data, setData] = useState<BatchSentimentResult | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchSentiment = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getSentiment(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch sentiment distribution');
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
      fetchSentiment();
    }
  }, [fetchSentiment, autoFetch]);

  return { data, loading, error, refetch: fetchSentiment };
}

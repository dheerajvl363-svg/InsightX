import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { TopicListResponse, AnalyticsQueryParams } from '../types/api';

export interface UseTopicsReturn {
  data: TopicListResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useTopics(
  params: AnalyticsQueryParams = {},
  autoFetch = true
): UseTopicsReturn {
  const [data, setData] = useState<TopicListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchTopics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getTopics(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch topic clusters');
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
      fetchTopics();
    }
  }, [fetchTopics, autoFetch]);

  return { data, loading, error, refetch: fetchTopics };
}

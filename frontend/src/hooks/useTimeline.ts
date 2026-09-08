import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { TimelineResponse } from '../types/api';

export interface UseTimelineReturn {
  data: TimelineResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useTimeline(
  granularity: 'hour' | 'day' | 'week' = 'day',
  platform?: string,
  autoFetch = true
): UseTimelineReturn {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getTimeline(granularity, platform);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch timeline volume points');
      }
    } finally {
      setLoading(false);
    }
  }, [granularity, platform]);

  useEffect(() => {
    if (autoFetch) {
      fetchTimeline();
    }
  }, [fetchTimeline, autoFetch]);

  return { data, loading, error, refetch: fetchTimeline };
}

import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { DashboardOverviewResponse, AnalyticsQueryParams } from '../types/api';

export interface UseOverviewReturn {
  data: DashboardOverviewResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useOverview(
  params: AnalyticsQueryParams = {},
  autoFetch = true
): UseOverviewReturn {
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getOverview(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch dashboard overview snapshot');
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
      fetchOverview();
    }
  }, [fetchOverview, autoFetch]);

  return { data, loading, error, refetch: fetchOverview };
}

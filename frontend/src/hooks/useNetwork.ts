import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { BatchNetworkResult, AnalyticsQueryParams } from '../types/api';

export interface UseNetworkReturn {
  data: BatchNetworkResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useNetwork(
  params: AnalyticsQueryParams = {},
  autoFetch = true
): UseNetworkReturn {
  const [data, setData] = useState<BatchNetworkResult | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchNetwork = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getNetworkGraph(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch interaction network graph');
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
      fetchNetwork();
    }
  }, [fetchNetwork, autoFetch]);

  return { data, loading, error, refetch: fetchNetwork };
}

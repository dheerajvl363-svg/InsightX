import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { InsightExplanation } from '../types/api';

export interface UseInsightExplanationReturn {
  data: InsightExplanation | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useInsightExplanation(
  insightId: string | null,
  platform?: string
): UseInsightExplanationReturn {
  const [data, setData] = useState<InsightExplanation | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(insightId));
  const [error, setError] = useState<string | null>(null);

  const fetchExplanation = useCallback(async () => {
    if (!insightId) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getInsightExplanation(insightId, platform);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch insight explanation and audit trace');
      }
    } finally {
      setLoading(false);
    }
  }, [insightId, platform]);

  useEffect(() => {
    fetchExplanation();
  }, [fetchExplanation]);

  return { data, loading, error, refetch: fetchExplanation };
}

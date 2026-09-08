import { useState, useEffect, useCallback } from 'react';
import { apiService, ApiError } from '../services/api';
import type { PostListResponse, PostQueryParams } from '../types/api';

export interface UsePostsReturn {
  data: PostListResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function usePosts(
  params: PostQueryParams = {},
  autoFetch = true
): UsePostsReturn {
  const [data, setData] = useState<PostListResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<string | null>(null);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getPosts(params);
      setData(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch posts from database');
      }
    } finally {
      setLoading(false);
    }
  }, [
    params.platform,
    params.language,
    params.search,
    params.keyword,
    params.author,
    params.sentiment,
    params.start_date,
    params.end_date,
    params.min_likes,
    params.min_comments,
    params.min_shares,
    params.min_views,
    params.sort_by,
    params.order,
    params.limit,
    params.offset,
  ]);

  useEffect(() => {
    if (autoFetch) {
      fetchPosts();
    }
  }, [fetchPosts, autoFetch]);

  return { data, loading, error, refetch: fetchPosts };
}

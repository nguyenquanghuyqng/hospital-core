/**
 * useAsync — wrapper cho async operations.
 * Tiêu chí 9: error/loading/empty state thống nhất.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { getErrorMessage } from '@lib/utils';

interface AsyncState<T> {
  data:    T | null;
  loading: boolean;
  error:   string | null;
}

interface UseAsyncReturn<T> extends AsyncState<T> {
  run:   (promise: Promise<T>) => Promise<T | null>;
  reset: () => void;
}

export function useAsync<T = unknown>(): UseAsyncReturn<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null, loading: false, error: null,
  });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const run = useCallback(async (promise: Promise<T>): Promise<T | null> => {
    setState({ data: null, loading: true, error: null });
    try {
      const data = await promise;
      if (mountedRef.current) setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = getErrorMessage(err);
      if (mountedRef.current) setState({ data: null, loading: false, error });
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, run, reset };
}

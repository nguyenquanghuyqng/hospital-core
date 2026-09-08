import { useState, useCallback } from 'react';

interface UsePaginationOptions {
  initialPage?:     number;
  initialPageSize?: number;
}

export function usePagination({ initialPage = 1, initialPageSize = 20 }: UsePaginationOptions = {}) {
  const [page,     setPage]     = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const goTo    = useCallback((p: number) => setPage(p), []);
  const reset   = useCallback(() => setPage(1), []);
  const resize  = useCallback((ps: number) => { setPageSize(ps); setPage(1); }, []);

  return { page, pageSize, goTo, reset, resize };
}

import { useState, useCallback, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { type SortingState } from '@tanstack/react-table';

export interface TableState {
  page: number;
  pageSize: number;
  search: string;
  sorting: SortingState;
  filters: Record<string, string>;
}

export interface UseTableStateOptions {
  defaultPageSize?: number;
  defaultSorting?: SortingState;
  syncWithUrl?: boolean;
  filterKeys?: string[];
}

export function useTableState(options: UseTableStateOptions = {}) {
  const {
    defaultPageSize = 10,
    defaultSorting = [],
    syncWithUrl = true,
    filterKeys = [],
  } = options;

  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize state from URL params or defaults
  const getInitialState = useCallback((): TableState => {
    if (syncWithUrl) {
      const page = parseInt(searchParams.get('page') || '1', 10);
      const pageSize = parseInt(searchParams.get('page_size') || String(defaultPageSize), 10);
      const search = searchParams.get('search') || '';
      const ordering = searchParams.get('ordering') || '';

      // Parse sorting from URL
      const sorting: SortingState = ordering
        ? [{
            id: ordering.startsWith('-') ? ordering.slice(1) : ordering,
            desc: ordering.startsWith('-'),
          }]
        : defaultSorting;

      // Parse filters from URL
      const filters: Record<string, string> = {};
      filterKeys.forEach((key) => {
        const value = searchParams.get(key);
        if (value) filters[key] = value;
      });

      return { page, pageSize, search, sorting, filters };
    }

    return {
      page: 1,
      pageSize: defaultPageSize,
      search: '',
      sorting: defaultSorting,
      filters: {},
    };
  }, [syncWithUrl, searchParams, defaultPageSize, defaultSorting, filterKeys]);

  const [state, setState] = useState<TableState>(getInitialState);

  // Sync state to URL
  useEffect(() => {
    if (!syncWithUrl) return;

    const params = new URLSearchParams();

    if (state.page > 1) params.set('page', String(state.page));
    if (state.pageSize !== defaultPageSize) params.set('page_size', String(state.pageSize));
    if (state.search) params.set('search', state.search);

    if (state.sorting.length > 0) {
      const sort = state.sorting[0];
      params.set('ordering', sort.desc ? `-${sort.id}` : sort.id);
    }

    Object.entries(state.filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });

    setSearchParams(params, { replace: true });
  }, [state, syncWithUrl, setSearchParams, defaultPageSize]);

  // Actions
  const setPage = useCallback((page: number) => {
    setState((prev) => ({ ...prev, page }));
  }, []);

  const setPageSize = useCallback((pageSize: number) => {
    setState((prev) => ({ ...prev, pageSize, page: 1 }));
  }, []);

  const setSearch = useCallback((search: string) => {
    setState((prev) => ({ ...prev, search, page: 1 }));
  }, []);

  const setSorting = useCallback((sorting: SortingState) => {
    setState((prev) => ({ ...prev, sorting, page: 1 }));
  }, []);

  const setFilter = useCallback((key: string, value: string) => {
    setState((prev) => ({
      ...prev,
      filters: { ...prev.filters, [key]: value },
      page: 1,
    }));
  }, []);

  const clearFilters = useCallback(() => {
    setState((prev) => ({
      ...prev,
      filters: {},
      search: '',
      page: 1,
    }));
  }, []);

  const resetState = useCallback(() => {
    setState({
      page: 1,
      pageSize: defaultPageSize,
      search: '',
      sorting: defaultSorting,
      filters: {},
    });
  }, [defaultPageSize, defaultSorting]);

  // Build query params for API
  const queryParams = useMemo(() => {
    const params: Record<string, string | number> = {
      page: state.page,
      page_size: state.pageSize,
    };

    if (state.search) params.search = state.search;

    if (state.sorting.length > 0) {
      const sort = state.sorting[0];
      params.ordering = sort.desc ? `-${sort.id}` : sort.id;
    }

    Object.entries(state.filters).forEach(([key, value]) => {
      if (value) params[key] = value;
    });

    return params;
  }, [state]);

  return {
    ...state,
    queryParams,
    setPage,
    setPageSize,
    setSearch,
    setSorting,
    setFilter,
    clearFilters,
    resetState,
  };
}

import React, { useState, useCallback, useEffect } from 'react';
import { MagnifyingGlassIcon, XMarkIcon, FunnelIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { cn, debounce } from '../../lib/utils';
import { Button } from '../ui/Button';
import { Select, SelectOption } from '../ui/Select';
import { Badge } from '../ui/Badge';

export interface FilterConfig {
  key: string;
  label: string;
  type: 'select' | 'date' | 'dateRange';
  options?: SelectOption[];
  placeholder?: string;
}

export interface FilterBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  filters?: FilterConfig[];
  filterValues?: Record<string, string>;
  onFilterChange?: (key: string, value: string) => void;
  onClearFilters?: () => void;
  debounceMs?: number;
  placeholder?: string;
  className?: string;
  showActiveFilters?: boolean;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchValue,
  onSearchChange,
  filters = [],
  filterValues = {},
  onFilterChange,
  onClearFilters,
  debounceMs = 300,
  placeholder = 'Search...',
  className,
  showActiveFilters = true,
}) => {
  const [localSearch, setLocalSearch] = useState(searchValue);
  const [showFilters, setShowFilters] = useState(false);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((value: string) => {
      onSearchChange(value);
    }, debounceMs),
    [onSearchChange, debounceMs]
  );

  // Update local search when prop changes
  useEffect(() => {
    setLocalSearch(searchValue);
  }, [searchValue]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalSearch(value);
    debouncedSearch(value);
  };

  const handleClearSearch = () => {
    setLocalSearch('');
    onSearchChange('');
  };

  // Get active filter count
  const activeFilterCount = Object.values(filterValues).filter(Boolean).length;

  // Get active filters for chips
  const activeFilters = filters
    .filter((f) => filterValues[f.key])
    .map((f) => ({
      ...f,
      value: filterValues[f.key],
      displayValue: f.options?.find((o) => o.value === filterValues[f.key])?.label || filterValues[f.key],
    }));

  return (
    <div className={cn('space-y-4', className)}>
      {/* Main search and filter toggle */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search input */}
        <div className="relative flex-1">
          <MagnifyingGlassIcon
            className="pointer-events-none absolute inset-y-0 left-3 h-full w-5 text-slate-400"
            aria-hidden="true"
          />
          <input
            type="search"
            value={localSearch}
            onChange={handleSearchChange}
            placeholder={placeholder}
            className={cn(
              'block w-full h-10 rounded-xl border-0 py-0 pl-10 pr-10',
              'bg-white dark:bg-dark-elevated',
              'text-slate-900 dark:text-slate-100 placeholder:text-slate-400',
              'ring-1 ring-inset ring-light-border dark:ring-dark-border',
              'focus:ring-2 focus:ring-inset focus:ring-brand-500',
              'text-sm transition-all duration-200'
            )}
          />
          {localSearch && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute inset-y-0 right-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Filter toggle button */}
        {filters.length > 0 && (
          <Button
            variant={showFilters ? 'primary' : 'secondary'}
            onClick={() => setShowFilters(!showFilters)}
            className="relative"
          >
            <FunnelIcon className="h-4 w-4" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-1 inline-flex items-center justify-center h-5 w-5 rounded-full bg-white/20 text-xs font-medium">
                {activeFilterCount}
              </span>
            )}
          </Button>
        )}
      </div>

      {/* Expanded filters */}
      {showFilters && filters.length > 0 && (
        <div className="flex flex-wrap gap-3 p-4 bg-slate-50 dark:bg-dark-elevated rounded-xl animate-fade-in">
          {filters.map((filter) => (
            <div key={filter.key} className="min-w-[180px]">
              {filter.type === 'select' && filter.options && (
                <Select
                  label={filter.label}
                  options={[{ value: '', label: filter.placeholder || 'All' }, ...filter.options]}
                  value={filterValues[filter.key] || ''}
                  onChange={(value) => onFilterChange?.(filter.key, value)}
                />
              )}
              {filter.type === 'date' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                    {filter.label}
                  </label>
                  <div className="relative">
                    <CalendarIcon className="pointer-events-none absolute inset-y-0 left-3 h-full w-4 text-slate-400" />
                    <input
                      type="date"
                      value={filterValues[filter.key] || ''}
                      onChange={(e) => onFilterChange?.(filter.key, e.target.value)}
                      className={cn(
                        'block w-full h-10 rounded-xl border-0 py-0 pl-9 pr-3',
                        'bg-white dark:bg-dark-card',
                        'text-slate-900 dark:text-slate-100',
                        'ring-1 ring-inset ring-light-border dark:ring-dark-border',
                        'focus:ring-2 focus:ring-inset focus:ring-brand-500',
                        'text-sm'
                      )}
                    />
                  </div>
                </div>
              )}
              {filter.type === 'dateRange' && (
                <div className="flex gap-2">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      {filter.label} From
                    </label>
                    <input
                      type="date"
                      value={filterValues[`${filter.key}_from`] || ''}
                      onChange={(e) => onFilterChange?.(`${filter.key}_from`, e.target.value)}
                      className={cn(
                        'block w-full h-10 rounded-xl border-0 py-0 px-3',
                        'bg-white dark:bg-dark-card',
                        'text-slate-900 dark:text-slate-100',
                        'ring-1 ring-inset ring-light-border dark:ring-dark-border',
                        'focus:ring-2 focus:ring-inset focus:ring-brand-500',
                        'text-sm'
                      )}
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      {filter.label} To
                    </label>
                    <input
                      type="date"
                      value={filterValues[`${filter.key}_to`] || ''}
                      onChange={(e) => onFilterChange?.(`${filter.key}_to`, e.target.value)}
                      className={cn(
                        'block w-full h-10 rounded-xl border-0 py-0 px-3',
                        'bg-white dark:bg-dark-card',
                        'text-slate-900 dark:text-slate-100',
                        'ring-1 ring-inset ring-light-border dark:ring-dark-border',
                        'focus:ring-2 focus:ring-inset focus:ring-brand-500',
                        'text-sm'
                      )}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}

          {activeFilterCount > 0 && onClearFilters && (
            <div className="flex items-end">
              <Button variant="ghost" size="sm" onClick={onClearFilters}>
                <XMarkIcon className="h-4 w-4" />
                Clear all
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Active filter chips */}
      {showActiveFilters && activeFilters.length > 0 && !showFilters && (
        <div className="flex flex-wrap gap-2">
          {activeFilters.map((filter) => (
            <Badge key={filter.key} variant="primary" className="pl-2 pr-1 py-1">
              <span className="text-xs opacity-70 mr-1">{filter.label}:</span>
              {filter.displayValue}
              <button
                type="button"
                onClick={() => onFilterChange?.(filter.key, '')}
                className="ml-1 p-0.5 rounded hover:bg-brand-600/20"
              >
                <XMarkIcon className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {onClearFilters && (
            <Button variant="ghost" size="sm" onClick={onClearFilters}>
              Clear all
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

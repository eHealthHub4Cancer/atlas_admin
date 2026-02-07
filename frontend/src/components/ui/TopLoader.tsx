import React from 'react';
import { useIsFetching, useIsMutating } from '@tanstack/react-query';

export const TopLoader: React.FC = () => {
  const isFetching = useIsFetching();
  const isMutating = useIsMutating();
  const active = isFetching + isMutating > 0;

  return (
    <div
      className={`top-loader ${active ? 'active' : ''}`}
      role="progressbar"
      aria-hidden={!active}
      aria-label="Loading"
    />
  );
};

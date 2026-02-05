import React, { Fragment, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  MagnifyingGlassIcon,
  BellIcon,
  SunIcon,
  MoonIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';
import { useThemeStore } from '../../store/theme';
import { useAuthStore } from '../../store/auth';
import { cn, getInitials } from '../../lib/utils';

export interface HeaderProps {
  onMenuClick?: () => void;
  showMenuButton?: boolean;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export const Header: React.FC<HeaderProps> = ({
  onMenuClick,
  showMenuButton = true,
  breadcrumbs = [],
}) => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useThemeStore();
  const { session, logout } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const displayName = session?.display_name || session?.username || 'User';

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-light-border dark:border-dark-border bg-white/80 dark:bg-dark-bg/80 backdrop-blur-xl px-4 sm:gap-x-6 sm:px-6 lg:px-8">
      {/* Mobile menu button */}
      {showMenuButton && (
        <button
          type="button"
          className="p-2.5 -m-2.5 text-slate-700 dark:text-slate-300 lg:hidden"
          onClick={onMenuClick}
        >
          <span className="sr-only">Open sidebar</span>
          <Bars3Icon className="h-6 w-6" aria-hidden="true" />
        </button>
      )}

      {/* Separator */}
      {showMenuButton && (
        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 lg:hidden" aria-hidden="true" />
      )}

      <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
        {/* Breadcrumbs */}
        {breadcrumbs.length > 0 && (
          <nav className="hidden sm:flex items-center" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-2">
              {breadcrumbs.map((crumb, index) => (
                <li key={index} className="flex items-center">
                  {index > 0 && (
                    <svg
                      className="h-4 w-4 flex-shrink-0 text-slate-400 mx-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path d="M5.555 17.776l8-16 .894.448-8 16-.894-.448z" />
                    </svg>
                  )}
                  {crumb.href ? (
                    <Link
                      to={crumb.href}
                      className="text-sm font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                    >
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {crumb.label}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}

        {/* Search */}
        <div className="flex flex-1 items-center justify-end gap-x-4 lg:gap-x-6">
          <form className="relative flex-1 max-w-md" action="#" method="GET">
            <label htmlFor="search-field" className="sr-only">
              Search
            </label>
            <MagnifyingGlassIcon
              className="pointer-events-none absolute inset-y-0 left-3 h-full w-5 text-slate-400"
              aria-hidden="true"
            />
            <input
              id="search-field"
              className={cn(
                'block w-full h-10 rounded-xl border-0 py-0 pl-10 pr-4',
                'bg-slate-100 dark:bg-dark-elevated',
                'text-slate-900 dark:text-slate-100 placeholder:text-slate-400',
                'focus:ring-2 focus:ring-inset focus:ring-brand-500',
                'text-sm transition-all duration-200'
              )}
              placeholder="Search..."
              type="search"
              name="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </form>

          {/* Theme toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className={cn(
              'relative p-2 rounded-xl',
              'text-slate-500 dark:text-slate-400',
              'hover:bg-slate-100 dark:hover:bg-dark-elevated',
              'hover:text-slate-700 dark:hover:text-slate-200',
              'transition-all duration-200'
            )}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <SunIcon className="h-5 w-5" aria-hidden="true" />
            ) : (
              <MoonIcon className="h-5 w-5" aria-hidden="true" />
            )}
          </button>

          {/* Notifications */}
          <button
            type="button"
            className={cn(
              'relative p-2 rounded-xl',
              'text-slate-500 dark:text-slate-400',
              'hover:bg-slate-100 dark:hover:bg-dark-elevated',
              'hover:text-slate-700 dark:hover:text-slate-200',
              'transition-all duration-200'
            )}
          >
            <span className="sr-only">View notifications</span>
            <BellIcon className="h-5 w-5" aria-hidden="true" />
            {/* Notification badge */}
            <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-dark-bg" />
          </button>

          {/* Separator */}
          <div
            className="hidden lg:block lg:h-6 lg:w-px lg:bg-slate-200 dark:lg:bg-slate-700"
            aria-hidden="true"
          />

          {/* Profile dropdown */}
          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center gap-3 p-1.5 -m-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-dark-elevated transition-colors">
              <span className="sr-only">Open user menu</span>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-500 text-white text-sm font-medium">
                {getInitials(displayName)}
              </div>
              <span className="hidden lg:flex lg:items-center">
                <span className="text-sm font-semibold leading-6 text-slate-900 dark:text-slate-100" aria-hidden="true">
                  {displayName}
                </span>
                <svg className="ml-2 h-5 w-5 text-slate-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                    clipRule="evenodd"
                  />
                </svg>
              </span>
            </Menu.Button>
            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 z-10 mt-2.5 w-48 origin-top-right rounded-xl bg-white dark:bg-dark-card border border-light-border dark:border-dark-border shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                <div className="py-1">
                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to="/user/profile"
                        className={cn(
                          'flex items-center gap-2 px-4 py-2 text-sm',
                          active ? 'bg-slate-100 dark:bg-dark-elevated' : '',
                          'text-slate-700 dark:text-slate-300'
                        )}
                      >
                        <UserCircleIcon className="h-4 w-4" />
                        Your Profile
                      </Link>
                    )}
                  </Menu.Item>
                  <Menu.Item>
                    {({ active }) => (
                      <Link
                        to="/user/settings"
                        className={cn(
                          'flex items-center gap-2 px-4 py-2 text-sm',
                          active ? 'bg-slate-100 dark:bg-dark-elevated' : '',
                          'text-slate-700 dark:text-slate-300'
                        )}
                      >
                        <Cog6ToothIcon className="h-4 w-4" />
                        Settings
                      </Link>
                    )}
                  </Menu.Item>
                  <div className="border-t border-light-border dark:border-dark-border my-1" />
                  <Menu.Item>
                    {({ active }) => (
                      <button
                        onClick={handleLogout}
                        className={cn(
                          'flex w-full items-center gap-2 px-4 py-2 text-sm',
                          active ? 'bg-slate-100 dark:bg-dark-elevated' : '',
                          'text-red-600 dark:text-red-400'
                        )}
                      >
                        <ArrowRightOnRectangleIcon className="h-4 w-4" />
                        Sign out
                      </button>
                    )}
                  </Menu.Item>
                </div>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  );
};

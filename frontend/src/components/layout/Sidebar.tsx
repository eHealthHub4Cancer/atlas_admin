import React, { Fragment } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';

export interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number;
}

export interface SidebarProps {
  navigation: NavItem[];
  mobileOpen: boolean;
  onMobileClose: () => void;
  logo?: React.ReactNode;
  title?: string;
  subtitle?: string;
}

const NavLink: React.FC<{ item: NavItem; isCurrent: boolean }> = ({ item, isCurrent }) => {
  return (
    <Link
      to={item.href}
      className={cn(
        'group flex items-center gap-x-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200',
        isCurrent
          ? 'bg-brand-500 text-white shadow-md shadow-brand-500/30'
          : 'text-black dark:text-white hover:bg-slate-100 dark:hover:bg-dark-elevated hover:text-black dark:hover:text-white'
      )}
    >
      <item.icon
        className={cn(
          'h-5 w-5 shrink-0 transition-colors',
          isCurrent ? 'text-white' : 'text-black dark:text-white group-hover:text-black dark:group-hover:text-white'
        )}
        aria-hidden="true"
      />
      <span className="truncate">{item.name}</span>
      {item.badge !== undefined && (
        <span
          className={cn(
            'ml-auto text-xs font-semibold px-2 py-0.5 rounded-full',
            isCurrent
              ? 'bg-white/20 text-white'
              : 'bg-slate-200 dark:bg-dark-elevated text-black dark:text-white'
          )}
        >
          {item.badge}
        </span>
      )}
    </Link>
  );
};

const SidebarContent: React.FC<{
  navigation: NavItem[];
  logo?: React.ReactNode;
  title?: string;
  subtitle?: string;
  pathname: string;
}> = ({ navigation, logo, title, subtitle, pathname }) => {
  return (
    <div className="flex grow min-h-0 flex-col gap-y-5 overflow-y-auto px-4 py-6">
      {/* Logo */}
      <div className="flex h-12 shrink-0 items-center gap-3 px-2">
        {logo || (
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500 text-white font-bold text-lg">
            A
          </div>
        )}
        <div>
          <h1 className="text-lg font-bold text-slate-900 dark:text-slate-100">
            {title || 'Atlas'}
          </h1>
          {subtitle && (
            <p className="text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex min-h-0 flex-1 flex-col">
        <ul role="list" className="flex min-h-0 flex-1 flex-col gap-y-1">
          {navigation.map((item) => (
            <li key={item.name}>
              <NavLink item={item} isCurrent={pathname === item.href} />
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
};

export const Sidebar: React.FC<SidebarProps> = ({
  navigation,
  mobileOpen,
  onMobileClose,
  logo,
  title,
  subtitle,
}) => {
  const location = useLocation();

  return (
    <>
      {/* Mobile sidebar */}
      <Transition.Root show={mobileOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50 lg:hidden" onClose={onMobileClose}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          </Transition.Child>

          <div className="fixed inset-0 flex">
            <Transition.Child
              as={Fragment}
              enter="transition ease-in-out duration-300 transform"
              enterFrom="-translate-x-full"
              enterTo="translate-x-0"
              leave="transition ease-in-out duration-300 transform"
              leaveFrom="translate-x-0"
              leaveTo="-translate-x-full"
            >
              <Dialog.Panel className="relative mr-16 flex h-full w-full max-w-xs flex-1">
                <Transition.Child
                  as={Fragment}
                  enter="ease-in-out duration-300"
                  enterFrom="opacity-0"
                  enterTo="opacity-100"
                  leave="ease-in-out duration-300"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <div className="absolute left-full top-0 flex w-16 justify-center pt-5">
                    <button
                      type="button"
                      className="-m-2.5 p-2.5"
                      onClick={onMobileClose}
                    >
                      <span className="sr-only">Close sidebar</span>
                      <XMarkIcon className="h-6 w-6 text-white" aria-hidden="true" />
                    </button>
                  </div>
                </Transition.Child>
                <div className="flex h-full min-h-0 grow flex-col gap-y-5 overflow-y-auto bg-white dark:bg-dark-card border-r border-light-border dark:border-dark-border">
                  <SidebarContent
                    navigation={navigation}
                    logo={logo}
                    title={title}
                    subtitle={subtitle}
                    pathname={location.pathname}
                  />
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </Dialog>
      </Transition.Root>

      {/* Desktop sidebar */}
      <div className="app-sidebar hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:h-screen lg:w-64 lg:flex-col">
        <div className="flex h-full min-h-0 grow flex-col gap-y-5 overflow-y-auto border-r border-light-border dark:border-dark-border bg-white dark:bg-dark-card">
          <SidebarContent
            navigation={navigation}
            logo={logo}
            title={title}
            subtitle={subtitle}
            pathname={location.pathname}
          />
        </div>
      </div>
    </>
  );
};

import React from 'react';
import { Link } from 'react-router-dom';
import { useThemeStore } from '../../store/theme';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';
import { cn } from '../../lib/utils';

// Social icons
const GitHubIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
      clipRule="evenodd"
    />
  </svg>
);

const LinkedInIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
  </svg>
);

const XIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

export interface AuthLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  showAdminLink?: boolean;
  maxWidthClassName?: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title = 'Welcome to Atlas',
  subtitle = 'Sign in to your account',
  showAdminLink = false,
  maxWidthClassName = 'max-w-md',
}) => {
  const { theme, toggleTheme } = useThemeStore();

  return (
    <div className="relative min-h-screen overflow-hidden bg-light-bg dark:bg-dark-bg flex flex-col">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-20 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-brand-200/40 blur-3xl dark:bg-brand-500/20" />
        <div className="absolute bottom-0 right-0 h-80 w-80 translate-x-1/3 translate-y-1/3 rounded-full bg-sky-200/50 blur-3xl dark:bg-sky-500/20" />
      </div>
      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-dark-bg/70 backdrop-blur">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500 text-white font-bold text-lg shadow-glow-sm">
            A
          </div>
          <span className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Atlas
          </span>
        </Link>

        <div className="flex items-center gap-4">
          {showAdminLink && (
            <Link
              to="/admin-login"
              className="text-sm text-slate-600 dark:text-slate-400 hover:text-brand-500 dark:hover:text-brand-400 transition-colors"
            >
              Admin Login
            </Link>
          )}
          <button
            type="button"
            onClick={toggleTheme}
            className={cn(
              'p-2 rounded-xl',
              'text-slate-500 dark:text-slate-400',
              'hover:bg-slate-100 dark:hover:bg-dark-elevated',
              'hover:text-slate-700 dark:hover:text-slate-200',
              'transition-all duration-200'
            )}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <SunIcon className="h-5 w-5" />
            ) : (
              <MoonIcon className="h-5 w-5" />
            )}
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-6xl">
          <div className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-6 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 rounded-full border border-slate-200/70 bg-white/80 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 shadow-sm dark:border-slate-800/70 dark:bg-dark-card/70 dark:text-slate-400">
                Atlas Research Platform
              </div>
              <h1 className="text-3xl font-semibold leading-tight text-slate-900 dark:text-slate-100 sm:text-4xl">
                Streamline your research workflows in one secure hub.
              </h1>
              <p className="text-base text-slate-600 dark:text-slate-400">
                Manage datasets, collaborate with your team, and access insights with confidence. Built for modern
                research teams who want clarity, speed, and security.
              </p>
              <div className="flex flex-wrap justify-center gap-3 text-sm text-slate-500 dark:text-slate-400 lg:justify-start">
                <span className="rounded-full border border-slate-200/70 px-3 py-1 dark:border-slate-800/70">
                  Secure access
                </span>
                <span className="rounded-full border border-slate-200/70 px-3 py-1 dark:border-slate-800/70">
                  Team-ready
                </span>
                <span className="rounded-full border border-slate-200/70 px-3 py-1 dark:border-slate-800/70">
                  Built for scale
                </span>
              </div>
            </div>

            <div className={cn('w-full', maxWidthClassName)}>
              <div className="mb-6 text-center">
                <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>
              </div>

              <div className="bg-white/90 dark:bg-dark-card/90 rounded-3xl border border-slate-200/70 dark:border-slate-800/70 shadow-[0_24px_60px_-32px_rgba(15,23,42,0.6)] p-6 sm:p-8 backdrop-blur">
                {children}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-6 px-6 border-t border-slate-200/60 dark:border-slate-800/60 bg-white/70 dark:bg-dark-bg/70 backdrop-blur">
        <div className="flex flex-col items-center gap-4 text-center">
          {/* Social links */}
          <div className="flex items-center gap-6">
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              aria-label="GitHub"
            >
              <GitHubIcon className="h-5 w-5" />
            </a>
            <a
              href="https://linkedin.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              aria-label="LinkedIn"
            >
              <LinkedInIcon className="h-5 w-5" />
            </a>
            <a
              href="https://x.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              aria-label="X (Twitter)"
            >
              <XIcon className="h-5 w-5" />
            </a>
          </div>

          {/* Copyright */}
          <p className="text-sm text-slate-500 dark:text-slate-400">
            &copy; {new Date().getFullYear()} Atlas Research Platform. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

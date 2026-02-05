import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, NavItem } from './Sidebar';
import { Header } from './Header';
import { Footer } from './Footer';
import { cn } from '../../lib/utils';

export interface DashboardLayoutProps {
  navigation: NavItem[];
  title?: string;
  subtitle?: string;
  logo?: React.ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  showFooter?: boolean;
  children?: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  navigation,
  title,
  subtitle,
  logo,
  breadcrumbs = [],
  showFooter = true,
  children,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-light-bg dark:bg-dark-bg">
      <Sidebar
        navigation={navigation}
        mobileOpen={sidebarOpen}
        onMobileClose={() => setSidebarOpen(false)}
        logo={logo}
        title={title}
        subtitle={subtitle}
      />

      <div className="lg:pl-64">
        <Header
          onMenuClick={() => setSidebarOpen(true)}
          breadcrumbs={breadcrumbs}
        />

        <main className={cn('flex flex-col min-h-[calc(100vh-4rem)]')}>
          <div className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
            {children || <Outlet />}
          </div>

          {showFooter && <Footer compact />}
        </main>
      </div>
    </div>
  );
};

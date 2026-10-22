// Layout Components
import React from 'react';
import { Link, Outlet, useLocation, NavLink } from 'react-router-dom';
import { useAuthStore } from '../hooks/useAuth';
import { useThemeStore } from '../hooks/useTheme';
import { Button } from './UI';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  const navItems = [
    { path: '/instances', label: 'Instances', icon: '📦' },
    { path: '/mods', label: 'Mods', icon: '🧩' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <aside className={`fixed top-0 left-0 h-full w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-200 z-40 ${location.pathname === '/login' || location.pathname === '/register' ? '-translate-x-full' : 'translate-x-0'}`}>
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <Link to="/instances" className="flex items-center gap-2">
            <span className="text-2xl">🛡️</span>
            <span className="text-xl font-bold text-gray-900 dark:text-gray-100">Sentinel Pilot</span>
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="w-20 justify-center"
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </Button>
          </div>

          {user && (
            <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-800">
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                {user.full_name?.[0] || user.email[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {user.full_name || user.email}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user.email}</p>
              </div>
            </div>
          )}

          <Button variant="secondary" onClick={logout} className="w-full" size="sm">
            Logout
          </Button>
        </div>
      </div>
    </aside>
  );
};

export const Header: React.FC = () => {
  const { theme, toggleTheme } = useThemeStore();

  return (
    <header className={`fixed top-0 right-0 left-64 h-16 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 z-30 flex items-center justify-between px-6`}>
      <div className="flex-1" />
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={toggleTheme}>
          {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
        </Button>
      </div>
    </header>
  );
};

export const Layout: React.FC = () => {
  const { isAuthenticated, fetchMe } = useAuthStore();
  const location = useLocation();

  React.useEffect(() => {
    if (isAuthenticated && (location.pathname === '/login' || location.pathname === '/register')) {
      fetchMe();
    }
  }, [isAuthenticated, location.pathname, fetchMe]);

  if (location.pathname === '/login' || location.pathname === '/register') {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <Header />
      <main className="pt-16 pl-64 pb-8 pr-8">
        <Outlet />
      </main>
    </div>
  );
};
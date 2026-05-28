import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Upload, ListChecks, FileText, Moon, Sun, LogOut, User, Settings, ChevronDown } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import Badge from './Badge';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const navItems = [
    { to: '/upload', icon: Upload, label: 'Upload' },
    { to: '/review', icon: ListChecks, label: 'Review Queue' },
    { to: '/files', icon: FileText, label: 'Files' },
    ...(isAdmin ? [{ to: '/lookups', icon: Settings, label: 'Lookups' }] : []),
  ];

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center px-4 mx-auto max-w-7xl">
          <div className="flex items-center space-x-2 mr-8">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">H</span>
            </div>
            <span className="text-xl font-semibold bg-gradient-to-r from-brand-600 to-brand-500 bg-clip-text text-transparent">
              HULK
            </span>
          </div>

          <nav className="flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={cn(
                    'flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                    isActive
                      ? 'bg-brand-100 text-brand-900 dark:bg-brand-900/30 dark:text-brand-300'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center space-x-4">
            {/* Organization Badge */}
            {user?.org && (
              <div className="hidden sm:flex items-center text-sm">
                <Badge variant="default">{user.org.name}</Badge>
              </div>
            )}

            {/* Dark Mode Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-accent transition-colors"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Moon className="h-5 w-5" />
              )}
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-accent transition-colors"
              >
                <div className="h-8 w-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                  <User className="h-4 w-4 text-brand-600" />
                </div>
                <div className="hidden sm:block text-left">
                  <div className="text-sm font-medium">{user?.first_name || user?.username}</div>
                  <div className="text-xs text-muted-foreground capitalize">{user?.role}</div>
                </div>
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              </button>

              {/* Dropdown */}
              {showUserMenu && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowUserMenu(false)}
                  />
                  <div className="absolute right-0 mt-2 w-64 bg-card border rounded-lg shadow-lg z-50 animate-slide-in">
                    <div className="p-3 border-b">
                      <div className="font-medium">{user?.username}</div>
                      <div className="text-sm text-muted-foreground">{user?.email}</div>
                      <div className="mt-2 flex items-center space-x-2">
                        <Badge variant={isAdmin ? 'info' : 'default'} size="sm">
                          {user?.role}
                        </Badge>
                        {user?.org && (
                          <Badge variant="default" size="sm">{user.org.name}</Badge>
                        )}
                      </div>
                    </div>
                    <div className="p-1">
                      <button
                        className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-accent transition-colors text-left"
                        onClick={() => {
                          setShowUserMenu(false);
                          // Navigate to settings
                        }}
                      >
                        <Settings className="h-4 w-4" />
                        <span>Settings</span>
                      </button>
                      <button
                        className="w-full flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors text-left"
                        onClick={handleLogout}
                      >
                        <LogOut className="h-4 w-4" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container px-4 py-8 mx-auto max-w-7xl">
        <div className="animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}

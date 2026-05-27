import { Link, useLocation } from 'react-router-dom';
import { Upload, ListChecks, FileText } from 'lucide-react';
import { cn } from '../lib/utils';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  const navItems = [
    { to: '/upload', icon: Upload, label: 'Upload' },
    { to: '/review', icon: ListChecks, label: 'Review Queue' },
    { to: '/files', icon: FileText, label: 'Files' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center px-4 mx-auto max-w-7xl">
          <div className="flex items-center space-x-2 mr-8">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">B</span>
            </div>
            <span className="text-xl font-semibold bg-gradient-to-r from-brand-600 to-brand-500 bg-clip-text text-transparent">
              Breathe ESG
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
            <div className="text-sm text-muted-foreground">
              Demo Corporation
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

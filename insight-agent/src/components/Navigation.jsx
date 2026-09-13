import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Database, Upload, Settings, MessageSquare, LayoutDashboard } from 'lucide-react';

const Navigation = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Datasets & Docs', icon: Upload },
    { path: '/dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
    { path: '/chat', label: 'AI Analyst', icon: MessageSquare },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Desktop & Tablet Sidebar */}
      <nav className="w-64 glass-card border-r border-white/5 h-full flex flex-col hidden md:flex shrink-0">
        <div className="p-6 border-b border-white/5">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-6 h-6 text-indigo-500" />
            InsightOS
          </h1>
        </div>
        <div className="flex-1 py-6 px-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path || 
              (item.path === '/dashboard' && location.pathname.startsWith('/dashboard'));
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
                  isActive 
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Mobile Bottom Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 glass-card bg-[#08080b]/95 border-t border-white/10 flex justify-around items-center py-2 px-2 backdrop-blur-2xl">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
            (item.path === '/dashboard' && location.pathname.startsWith('/dashboard'));
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition-all text-[11px] ${
                isActive 
                  ? 'text-indigo-400 font-semibold' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label === 'Executive Dashboard' ? 'Dashboard' : (item.label === 'Datasets & Docs' ? 'Assets' : item.label)}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
};

export default Navigation;


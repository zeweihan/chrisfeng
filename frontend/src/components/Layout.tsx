import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Home, Upload, Settings, LogOut, BarChart } from 'lucide-react';

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  const menu = [
    { name: '仪表盘', path: '/', icon: Home },
    { name: '上传数据', path: '/upload', icon: Upload },
    { name: '系统配置', path: '/admin', icon: Settings },
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar - Pro Max Style (Glass-dark) */}
      <aside className="w-64 fixed inset-y-0 left-0 bg-slate-900/95 backdrop-blur-xl border-r border-white/10 z-50 flex flex-col transition-all">
        <div className="h-20 flex items-center px-6 border-b border-white/10">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 mr-3">
            <BarChart size={20} />
          </div>
          <span className="text-white font-bold tracking-wide">HR Intelligence</span>
        </div>

        <nav className="flex-1 px-4 py-8 space-y-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-2 mb-4">功能菜单</div>
          {menu.map((item) => {
            const active = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group",
                  active 
                    ? "bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-md shadow-blue-500/20" 
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                )}
              >
                <Icon size={18} className={cn("transition-colors", active ? "text-white" : "text-slate-500 group-hover:text-slate-300")} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10">
          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-all group"
          >
            <LogOut size={18} className="text-slate-500 group-hover:text-slate-300" />
            退出登录
          </button>
        </div>
      </aside>

      {/* Main content wrapper */}
      <main className="ml-64 flex-1 flex flex-col min-h-screen relative overflow-x-hidden">
        <div className="absolute top-0 inset-x-0 h-64 bg-gradient-to-b from-blue-50/50 to-transparent -z-10 pointer-events-none"></div>
        <div className="flex-1 p-8">
          {children}
        </div>
      </main>
    </div>
  );
}

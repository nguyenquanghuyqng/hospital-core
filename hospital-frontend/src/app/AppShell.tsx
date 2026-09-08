/**
 * AppShell — layout chính: Sidebar + Topbar + content area.
 * Tiêu chí 1: component UI không chứa business logic.
 * Tiêu chí 8: menu items hiển thị theo permission.
 */
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '@features/auth/AuthContext';
import { ROUTES } from './routes';

interface NavItem {
  label:      string;
  icon:       string;
  to:         string;
  permission: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Tiếp đón',      icon: '🏥', to: ROUTES.RECEPTION, permission: 'reception' },
  { label: 'Hàng chờ',      icon: '🎫', to: ROUTES.QUEUE,     permission: 'queue'     },
  { label: 'Phòng khám',    icon: '🩺', to: ROUTES.DOCTOR,    permission: 'doctor'    },
];

export default function AppShell() {
  const { user, logout, can } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    toast.success('Đã đăng xuất');
    navigate(ROUTES.LOGIN, { replace: true });
  };

  const visibleItems = NAV_ITEMS.filter(item => can(item.permission));

  return (
    <div className="app-shell">
      {/* Overlay mobile */}
      {sidebarOpen && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', zIndex: 99 }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar${sidebarOpen ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">✚</div>
          <div>
            <div className="sidebar-brand-name">Thiện Nhân</div>
            <div className="sidebar-brand-sub">Phòng Khám Đa Khoa</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-title">Menu</div>
          <NavLink
            to={ROUTES.HOME}
            end
            className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
            onClick={() => setSidebarOpen(false)}
          >
            <span>🏠</span> Trang chủ
          </NavLink>

          {visibleItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <span>{item.icon}</span> {item.label}
            </NavLink>
          ))}

          <div className="sidebar-section-title" style={{ marginTop: 16 }}>Công cụ</div>
          <a
            href={ROUTES.KIOSK}
            target="_blank"
            rel="noopener noreferrer"
            className="sidebar-item"
          >
            <span>📟</span> Kiosk lấy số
          </a>
          <a
            href={ROUTES.DISPLAY}
            target="_blank"
            rel="noopener noreferrer"
            className="sidebar-item"
          >
            <span>📺</span> Màn hình LED
          </a>
        </nav>

        {/* User info */}
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 34, height: 34, borderRadius: '50%',
              background: 'var(--clr-primary)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '.85rem', fontWeight: 700, flexShrink: 0,
            }}>
              {(user?.full_name ?? user?.username ?? '?')[0]?.toUpperCase()}
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: '.82rem', fontWeight: 600, color: '#fff', lineHeight: 1.2 }} className="truncate">
                {user?.full_name ?? user?.username}
              </div>
              <div style={{ fontSize: '.7rem', color: 'rgba(255,255,255,.4)' }}>
                {user?.role} {user?.clinic_room ? `· ${user.clinic_room}` : ''}
              </div>
            </div>
          </div>
          <button className="sidebar-item" onClick={handleLogout} style={{ color: 'rgba(255,100,100,.8)' }}>
            <span>🚪</span> Đăng xuất
          </button>
        </div>
      </aside>

      {/* Topbar */}
      <header className="topbar">
        <button
          className="btn btn-ghost btn-icon"
          style={{ display: 'none' }}
          id="sidebar-toggle"
          onClick={() => setSidebarOpen(v => !v)}
          aria-label="Toggle sidebar"
        >
          ☰
        </button>
        <div className="topbar-title" id="page-title" />
        <div className="topbar-actions" id="topbar-actions" />
      </header>

      {/* Page content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

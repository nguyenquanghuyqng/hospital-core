import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { ROUTES } from '@/app/routes';

interface RoleCard {
  icon:        string;
  title:       string;
  description: string;
  to:          string;
  permission:  string;
  color:       string;
  bg:          string;
}

const ROLE_CARDS: RoleCard[] = [
  {
    icon: '🏥', title: 'Quầy Tiếp Đón',
    description: 'Đăng ký lượt khám, check-in bệnh nhân, quản lý hàng đợi tiếp đón.',
    to: ROUTES.RECEPTION, permission: 'reception',
    color: '#0284c7', bg: '#e0f2fe',
  },
  {
    icon: '🎫', title: 'Quản Lý Hàng Chờ',
    description: 'Gọi số thứ tự, theo dõi hàng đợi, điều phối bệnh nhân.',
    to: ROUTES.QUEUE, permission: 'queue',
    color: '#059669', bg: '#d1fae5',
  },
  {
    icon: '🩺', title: 'Phòng Khám Bác Sĩ',
    description: 'Xem danh sách bệnh nhân chờ khám, cập nhật trạng thái xử lý.',
    to: ROUTES.DOCTOR, permission: 'doctor',
    color: '#7c3aed', bg: '#ede9fe',
  },
];

export default function HomePage() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  const visible = ROLE_CARDS.filter(c => can(c.permission));

  return (
    <div className="page-container">
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--clr-gray-900)' }}>
          Xin chào, {user?.full_name ?? user?.username} 👋
        </h1>
        <p style={{ color: 'var(--clr-gray-500)', marginTop: 4 }}>
          Chọn chức năng phù hợp với vai trò của bạn.
        </p>
      </div>

      <div className="grid-3" style={{ gap: 20 }}>
        {visible.map(card => (
          <button
            key={card.to}
            onClick={() => navigate(card.to)}
            style={{
              background: '#fff', border: '2px solid var(--clr-gray-100)',
              borderRadius: 16, padding: 28, textAlign: 'left', cursor: 'pointer',
              transition: 'all .18s ease', display: 'flex', flexDirection: 'column', gap: 12,
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = card.color;
              (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-3px)';
              (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 8px 24px rgba(0,0,0,.10)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--clr-gray-100)';
              (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
              (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
            }}
          >
            <div style={{
              width: 52, height: 52, borderRadius: 14,
              background: card.bg, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '1.6rem',
            }}>
              {card.icon}
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--clr-gray-800)', marginBottom: 6 }}>
                {card.title}
              </div>
              <div style={{ fontSize: '.85rem', color: 'var(--clr-gray-500)', lineHeight: 1.6 }}>
                {card.description}
              </div>
            </div>
            <div style={{ color: card.color, fontSize: '.82rem', fontWeight: 600, marginTop: 'auto' }}>
              Truy cập →
            </div>
          </button>
        ))}
      </div>

      {/* Quick links */}
      <div style={{ marginTop: 40 }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--clr-gray-700)', marginBottom: 14 }}>
          Công cụ nhanh
        </h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <a href={ROUTES.KIOSK}   target="_blank" rel="noopener noreferrer"
            style={{ padding: '8px 16px', background: '#fff', border: '1px solid var(--clr-gray-200)', borderRadius: 8, fontSize: '.875rem', color: 'var(--clr-gray-700)', fontWeight: 500 }}>
            📟 Kiosk lấy số (màn hình riêng)
          </a>
          <a href={ROUTES.DISPLAY} target="_blank" rel="noopener noreferrer"
            style={{ padding: '8px 16px', background: '#fff', border: '1px solid var(--clr-gray-200)', borderRadius: 8, fontSize: '.875rem', color: 'var(--clr-gray-700)', fontWeight: 500 }}>
            📺 Màn hình LED hiển thị số
          </a>
        </div>
      </div>
    </div>
  );
}

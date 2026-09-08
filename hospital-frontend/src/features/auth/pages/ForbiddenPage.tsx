import { useNavigate } from 'react-router-dom';
import { Button } from '@components/ui';
import { ROUTES } from '@/app/routes';

export default function ForbiddenPage() {
  const navigate = useNavigate();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: 16 }}>🚫</div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 8 }}>Không có quyền truy cập</h1>
        <p style={{ color: 'var(--clr-gray-500)', marginBottom: 24 }}>
          Tài khoản của bạn không có quyền truy cập trang này.
        </p>
        <Button onClick={() => navigate(ROUTES.HOME)}>Về trang chủ</Button>
      </div>
    </div>
  );
}

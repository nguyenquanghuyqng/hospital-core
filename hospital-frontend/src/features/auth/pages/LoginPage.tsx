import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';
import { Button, Field } from '@components/ui';
import { ROUTES } from '@/app/routes';

const schema = z.object({
  username: z.string().min(1, 'Vui lòng nhập tên đăng nhập'),
  password: z.string().min(1, 'Vui lòng nhập mật khẩu'),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const navigate  = useNavigate();
  const location  = useLocation();
  const [loading, setLoading] = useState(false);
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? ROUTES.HOME;

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormValues) => {
    setLoading(true);
    try {
      await login(data.username, data.password);
      navigate(from, { replace: true });
    } catch (err) {
      toast.error((err as Error).message ?? 'Đăng nhập thất bại');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg,#0c2340,#0a3d62,#0ea5e9)', padding: 16,
    }}>
      <div style={{
        background: '#fff', borderRadius: 20, padding: 40, width: '100%', maxWidth: 400,
        boxShadow: '0 20px 60px rgba(0,0,0,.2)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 56, height: 56, background: 'linear-gradient(135deg,#0ea5e9,#0284c7)',
            borderRadius: 16, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 24, color: '#fff', marginBottom: 12,
          }}>✚</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--clr-gray-900)', lineHeight: 1.2 }}>
            {import.meta.env.VITE_APP_NAME ?? 'Phòng Khám Thiện Nhân'}
          </h1>
          <p style={{ fontSize: '.85rem', color: 'var(--clr-gray-500)', marginTop: 4 }}>
            Hệ thống quản lý phòng khám
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Field label="Tên đăng nhập" required error={errors.username?.message}>
            <input
              {...register('username')}
              className={`form-input${errors.username ? ' error' : ''}`}
              placeholder="Nhập tên đăng nhập"
              autoComplete="username"
              autoFocus
            />
          </Field>

          <Field label="Mật khẩu" required error={errors.password?.message}>
            <input
              {...register('password')}
              type="password"
              className={`form-input${errors.password ? ' error' : ''}`}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </Field>

          <Button type="submit" loading={loading} style={{ marginTop: 8 }}>
            Đăng nhập
          </Button>
        </form>
      </div>
    </div>
  );
}

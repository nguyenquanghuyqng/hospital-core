/**
 * Barrel export cho tất cả shared UI components.
 * Tiêu chí 10: Design system/component dùng lại được.
 */

// ── Button ────────────────────────────────────────────────────────────────────
import { type ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

type BtnVariant = 'primary' | 'secondary' | 'danger' | 'ghost';
type BtnSize    = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BtnVariant;
  size?: BtnSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, children, className, disabled, ...rest }, ref) => (
    <button
      ref={ref}
      className={clsx('btn', `btn-${variant}`, size !== 'md' && `btn-${size}`, className)}
      disabled={disabled ?? loading}
      {...rest}
    >
      {loading ? <Spinner size="sm" /> : icon}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';

// ── Spinner ────────────────────────────────────────────────────────────────────
interface SpinnerProps { size?: 'sm' | 'md' | 'lg'; className?: string }
export function Spinner({ size = 'md', className }: SpinnerProps) {
  return <span className={clsx('spinner', size !== 'md' && `spinner-${size}`, className)} aria-label="Loading" />;
}

// ── Badge ─────────────────────────────────────────────────────────────────────
interface BadgeProps { variant: string; children: React.ReactNode; className?: string }
export function Badge({ variant, children, className }: BadgeProps) {
  return (
    <span className={clsx('badge', `badge-${variant.toLowerCase().replace(/ /g, '_')}`, className)}>
      {children}
    </span>
  );
}

// ── Status Badge helpers ───────────────────────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  waiting: 'Chờ khám', calling: 'Đang gọi', serving: 'Đang phục vụ',
  done: 'Hoàn thành', skipped: 'Bỏ qua',
  pending: 'Chờ tiếp nhận', checked_in: 'Đã tiếp nhận',
  completed: 'Hoàn thành', cancelled: 'Đã huỷ',
  cls: 'Đi CLS', cls_result: 'Có KQ CLS', revisit: 'Tái khám',
  draft: 'Nháp', saved: 'Đã lưu',
};
export function StatusBadge({ status }: { status: string }) {
  return <Badge variant={status}>{STATUS_LABELS[status] ?? status}</Badge>;
}

// ── Card ──────────────────────────────────────────────────────────────────────
interface CardProps {
  title?: React.ReactNode;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}
export function Card({ title, actions, footer, children, className }: CardProps) {
  return (
    <div className={clsx('card', className)}>
      {(title ?? actions) && (
        <div className="card-header">
          {title && <span className="font-semibold text-base" style={{ color: 'var(--clr-gray-800)' }}>{title}</span>}
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
      )}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
  footer?: React.ReactNode;
}
export function Modal({ open, onClose, title, size, children, footer }: ModalProps) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={clsx('modal', size && `modal-${size}`)} role="dialog" aria-modal aria-labelledby="modal-title">
        <div className="modal-header">
          <h2 className="modal-title" id="modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Đóng">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}

// ── EmptyState ────────────────────────────────────────────────────────────────
interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}
export function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="state-box">
      <div className="state-box-icon">{icon}</div>
      <div className="state-box-title">{title}</div>
      {description && <div className="state-box-desc">{description}</div>}
      {action}
    </div>
  );
}

// ── ErrorState ────────────────────────────────────────────────────────────────
interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}
export function ErrorState({ message = 'Đã xảy ra lỗi. Vui lòng thử lại.', onRetry }: ErrorStateProps) {
  return (
    <div className="state-box">
      <div className="state-box-icon">⚠️</div>
      <div className="state-box-title">Lỗi tải dữ liệu</div>
      <div className="state-box-desc">{message}</div>
      {onRetry && <Button variant="ghost" size="sm" onClick={onRetry}>Thử lại</Button>}
    </div>
  );
}

// ── LoadingOverlay ─────────────────────────────────────────────────────────────
export function LoadingOverlay() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '64px' }}>
      <Spinner size="lg" />
    </div>
  );
}

// ── Confirm Dialog ─────────────────────────────────────────────────────────────
interface ConfirmProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title?: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
}
export function ConfirmDialog({ open, onClose, onConfirm, title = 'Xác nhận', message, confirmLabel = 'Xác nhận', danger }: ConfirmProps) {
  return (
    <Modal open={open} onClose={onClose} title={title} size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={() => { onConfirm(); onClose(); }}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p style={{ lineHeight: 1.7 }}>{message}</p>
    </Modal>
  );
}

// ── Form field wrappers ────────────────────────────────────────────────────────
interface FieldProps {
  label: string;
  required?: boolean;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}
export function Field({ label, required, error, hint, children }: FieldProps) {
  return (
    <div className="form-group">
      <label className="form-label">
        {label}{required && <span className="required">*</span>}
      </label>
      {children}
      {error && <span className="form-error">{error}</span>}
      {hint && !error && <span className="form-hint">{hint}</span>}
    </div>
  );
}

// ── Pagination ─────────────────────────────────────────────────────────────────
interface PaginationProps { page: number; totalPages: number; onChange: (p: number) => void }
export function Pagination({ page, totalPages, onChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  const pages = new Set([1, totalPages]);
  for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) pages.add(i);
  const sorted = [...pages].sort((a, b) => a - b);
  return (
    <div className="pagination">
      <button className="page-btn" disabled={page === 1} onClick={() => onChange(page - 1)}>‹</button>
      {sorted.map((p, i) => (
        <span key={p}>
          {i > 0 && sorted[i - 1] !== undefined && p - (sorted[i - 1]!) > 1 && (
            <span className="page-btn" style={{ border: 'none', cursor: 'default' }}>…</span>
          )}
          <button className={clsx('page-btn', p === page && 'active')} onClick={() => onChange(p)}>{p}</button>
        </span>
      ))}
      <button className="page-btn" disabled={page === totalPages} onClick={() => onChange(page + 1)}>›</button>
    </div>
  );
}

// ── Stat Card ──────────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;
  color?: string;
  bg?: string;
}
export function StatCard({ label, value, icon, color = 'var(--clr-primary)', bg = 'var(--clr-primary-light)' }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon" style={{ background: bg, color }}>{icon}</div>
      <div>
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
      </div>
    </div>
  );
}

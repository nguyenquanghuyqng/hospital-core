/** Utility helpers — không chứa business logic */

/** Format ISO date → DD/MM/YYYY */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleDateString('vi-VN');
}

/** Format ISO datetime → HH:mm DD/MM/YYYY */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? iso
    : d.toLocaleString('vi-VN', {
        hour: '2-digit', minute: '2-digit',
        day: '2-digit', month: '2-digit', year: 'numeric',
      });
}

/** Today YYYY-MM-DD */
export function today(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Gender label */
export function fmtGender(g: string | null | undefined): string {
  return g === 'male' ? 'Nam' : g === 'female' ? 'Nữ' : '—';
}

/** Priority label */
export function fmtPriority(p: number): string {
  return (['Bình thường', 'Ưu tiên', 'Cấp cứu'] as const)[p] ?? '—';
}

/** Pad number with leading zeros */
export function pad(n: number, len = 3): string {
  return String(n).padStart(len, '0');
}

/** Extract error message from unknown catch value */
export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return 'Đã xảy ra lỗi không xác định';
}

/** Build full address string from parts */
export function fmtAddress(parts: (string | null | undefined)[]): string {
  return parts.filter(Boolean).join(', ') || '—';
}

/** Visit status Vietnamese label */
export const VISIT_STATUS_LABELS: Record<string, string> = {
  waiting: 'Chờ khám', cls: 'Đi CLS', cls_result: 'Có KQ CLS',
  revisit: 'Tái khám', done: 'Hoàn thành',
};

/** Reception status label */
export const RECEPTION_STATUS_LABELS: Record<string, string> = {
  pending: 'Chờ tiếp nhận', checked_in: 'Đã tiếp nhận',
  completed: 'Hoàn thành', cancelled: 'Đã huỷ',
};

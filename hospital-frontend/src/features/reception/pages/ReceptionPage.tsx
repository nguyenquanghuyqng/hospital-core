/**
 * ReceptionPage — danh sách lượt tiếp đón trong ngày.
 * Tiêu chí 1: không chứa business logic — chỉ orchestrate API + store + UI.
 * Tiêu chí 9: loading/error/empty state thống nhất.
 */
import { useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { receptionApi } from '@api/reception.api';
import { useReceptionStore } from '@store/reception.store';
import { useAsync } from '@hooks/useAsync';
import { usePagination } from '@hooks/usePagination';
import { useWebSocket } from '@hooks/useWebSocket';
import {
  Button, Card, StatusBadge, EmptyState, ErrorState,
  LoadingOverlay, Pagination, StatCard, ConfirmDialog,
} from '@components/ui';
import { fmtDate, fmtDateTime, today } from '@lib/utils';
import { ROUTES, toPath } from '@/app/routes';
import type { ReceptionList } from '@/types';
import CheckInModal from '../components/CheckInModal';

export default function ReceptionPage() {
  const navigate  = useNavigate();
  const store     = useReceptionStore();
  const listAsync = useAsync<{ items: ReceptionList[]; total: number; total_pages: number }>();
  const { page, pageSize, goTo } = usePagination();

  const [checkInTarget, setCheckInTarget] = useState<ReceptionList | null>(null);
  const [cancelTarget,  setCancelTarget]  = useState<ReceptionList | null>(null);
  const cancelAsync = useAsync<unknown>();

  // ── Load list ──────────────────────────────────────────────────────────────
  const load = useCallback(() => {
    const { filters } = useReceptionStore.getState();
    listAsync.run(
      receptionApi.list({
        visit_date:  filters.visit_date ?? today(),
        status:      filters.status,
        clinic_room: filters.clinic_room,
        page, page_size: pageSize,
      }) as Promise<{ items: ReceptionList[]; total: number; total_pages: number }>,
    ).then(res => {
      if (res) store.setList(res.items, res.total);
    });
  }, [page, pageSize]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  // ── WebSocket real-time ────────────────────────────────────────────────────
  useWebSocket({
    room: 'reception',
    onMessage: (type) => {
      if (['reception_created', 'reception_updated', 'doctor_queue_update'].includes(type)) load();
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleCancel = async () => {
    if (!cancelTarget) return;
    const res = await cancelAsync.run(receptionApi.cancel(cancelTarget.id));
    if (res !== null) {
      toast.success('Đã huỷ lượt tiếp đón');
      load();
    } else {
      toast.error(cancelAsync.error ?? 'Huỷ thất bại');
    }
    setCancelTarget(null);
  };

  // ── Filters ────────────────────────────────────────────────────────────────
  const { filters } = store;

  return (
    <div className="page-container">
      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <StatCard label="Tổng hôm nay"   value={store.total} icon="📋" color="var(--clr-primary)"   bg="var(--clr-primary-light)" />
        <StatCard label="Chờ tiếp nhận"  value={store.list.filter(r => r.status === 'pending').length}   icon="⏳" color="#92400e" bg="#fef3c7" />
        <StatCard label="Đã tiếp nhận"   value={store.list.filter(r => r.status === 'checked_in').length} icon="✅" color="#1e40af" bg="#dbeafe" />
        <StatCard label="Hoàn thành"     value={store.list.filter(r => r.status === 'completed').length} icon="🏁" color="#065f46" bg="#d1fae5" />
      </div>

      <Card
        title="Danh sách lượt tiếp đón"
        actions={
          <div className="flex gap-2">
            <input
              type="date"
              className="form-input"
              style={{ padding: '6px 10px', fontSize: '.82rem' }}
              defaultValue={filters.visit_date ?? today()}
              onChange={e => { store.setFilters({ visit_date: e.target.value }); goTo(1); load(); }}
            />
            <select
              className="form-input"
              style={{ padding: '6px 10px', fontSize: '.82rem' }}
              defaultValue=""
              onChange={e => { store.setFilters({ status: e.target.value || undefined }); goTo(1); load(); }}
            >
              <option value="">Tất cả trạng thái</option>
              <option value="pending">Chờ tiếp nhận</option>
              <option value="checked_in">Đã tiếp nhận</option>
              <option value="completed">Hoàn thành</option>
              <option value="cancelled">Đã huỷ</option>
            </select>
            <Button size="sm" onClick={() => navigate(ROUTES.RECEPTION_NEW)}>
              + Đăng ký mới
            </Button>
          </div>
        }
      >
        {listAsync.loading && <LoadingOverlay />}
        {listAsync.error   && <ErrorState message={listAsync.error} onRetry={load} />}
        {!listAsync.loading && !listAsync.error && store.list.length === 0 && (
          <EmptyState icon="📋" title="Chưa có lượt tiếp đón nào" description="Nhấn '+ Đăng ký mới' để tạo lượt khám đầu tiên trong ngày." />
        )}
        {!listAsync.loading && store.list.length > 0 && (
          <>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>STT</th>
                    <th>Bệnh nhân</th>
                    <th>Giờ đăng ký</th>
                    <th>Phòng khám</th>
                    <th>Đối tượng</th>
                    <th>Trạng thái</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {store.list.map(r => (
                    <tr key={r.id}>
                      <td>
                        <span style={{
                          fontWeight: 700, fontSize: '1rem',
                          color: r.priority >= 2 ? 'var(--clr-danger)' : r.priority === 1 ? 'var(--clr-warning)' : 'var(--clr-gray-700)',
                        }}>
                          {r.visit_number ?? '—'}
                        </span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--clr-gray-800)' }}>
                          {r.patient?.full_name ?? '—'}
                        </div>
                        <div className="text-xs text-muted">{r.patient?.cccd ?? r.patient?.phone ?? ''}</div>
                      </td>
                      <td className="text-sm">{r.visit_time ?? fmtDate(r.visit_date)}</td>
                      <td className="text-sm">{r.clinic_room ?? '—'}</td>
                      <td className="text-sm">{r.subject_name ?? '—'}</td>
                      <td><StatusBadge status={r.status} /></td>
                      <td>
                        <div className="flex gap-2">
                          <Button
                            size="sm" variant="ghost"
                            onClick={() => navigate(toPath(ROUTES.RECEPTION_DETAIL, { id: r.id }))}
                          >
                            Chi tiết
                          </Button>
                          {r.status === 'pending' && (
                            <Button size="sm" onClick={() => setCheckInTarget(r)}>
                              Check-in
                            </Button>
                          )}
                          {(r.status === 'pending' || r.status === 'checked_in') && (
                            <Button size="sm" variant="danger" onClick={() => setCancelTarget(r)}>
                              Huỷ
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '14px 0 0' }}>
              <Pagination
                page={page}
                totalPages={listAsync.data?.total_pages ?? 1}
                onChange={goTo}
              />
            </div>
          </>
        )}
      </Card>

      {/* Check-in modal */}
      {checkInTarget && (
        <CheckInModal
          reception={checkInTarget}
          onClose={() => setCheckInTarget(null)}
          onSuccess={() => { setCheckInTarget(null); load(); }}
        />
      )}

      {/* Cancel confirm */}
      <ConfirmDialog
        open={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        onConfirm={handleCancel}
        title="Huỷ lượt tiếp đón"
        message={`Bạn có chắc muốn huỷ lượt khám của bệnh nhân ${cancelTarget?.patient?.full_name ?? ''}?`}
        confirmLabel="Huỷ lượt"
        danger
      />
    </div>
  );
}

import { useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { doctorApi } from '@api/doctor.api';
import { useAuth } from '@features/auth/AuthContext';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatCard, StatusBadge, EmptyState, LoadingOverlay, ConfirmDialog } from '@components/ui';
import { fmtDate, fmtGender, today, VISIT_STATUS_LABELS } from '@lib/utils';
import { ROUTES, toPath } from '@/app/routes';
import type { QueueItem, QueueStatsResponse, VisitStatus } from '@/types';
import TransferModal from '../components/TransferModal';

export default function DoctorQueuePage() {
  const { user }   = useAuth();
  const navigate   = useNavigate();
  const listAsync  = useAsync<QueueItem[]>();
  const statsAsync = useAsync<QueueStatsResponse>();

  const [clinicRoom, setClinicRoom] = useState(user?.clinic_room ?? '');
  const [visitDate,  setVisitDate]  = useState(today());
  const [transferTarget, setTransferTarget] = useState<QueueItem | null>(null);
  const [doneTarget,     setDoneTarget]     = useState<QueueItem | null>(null);

  const load = useCallback(() => {
    if (!clinicRoom) return;
    listAsync.run(doctorApi.queue({ clinic_room: clinicRoom, visit_date: visitDate }));
    statsAsync.run(doctorApi.stats({ clinic_room: clinicRoom, visit_date: visitDate }));
  }, [clinicRoom, visitDate]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  useWebSocket({
    room: 'reception',
    onMessage: (type) => {
      if (type === 'doctor_queue_update' || type === 'reception_updated') load();
    },
  });

  const handleVisitStatus = async (id: number, status: VisitStatus) => {
    await doctorApi.updateVisitStatus(id, status);
    toast.success(`Cập nhật: ${VISIT_STATUS_LABELS[status] ?? status}`);
    load();
  };

  const handleDone = async () => {
    if (!doneTarget) return;
    await doctorApi.completeVisit(doneTarget.id);
    toast.success('Đã hoàn thành lượt khám');
    setDoneTarget(null);
    load();
  };

  const s = statsAsync.data;

  return (
    <div className="page-container">
      {/* Filters */}
      <div className="flex gap-3 mb-4" style={{ flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <label className="form-label">Phòng khám</label>
          <input
            className="form-input" style={{ marginTop: 4, minWidth: 160 }}
            value={clinicRoom}
            placeholder="Nhập phòng khám..."
            onChange={e => setClinicRoom(e.target.value)}
          />
        </div>
        <div>
          <label className="form-label">Ngày khám</label>
          <input
            type="date" className="form-input" style={{ marginTop: 4 }}
            value={visitDate}
            onChange={e => setVisitDate(e.target.value)}
          />
        </div>
        <Button size="sm" variant="ghost" onClick={load}>↻ Làm mới</Button>
      </div>

      {/* Stats */}
      {s && (
        <div className="grid-4" style={{ marginBottom: 24 }}>
          <StatCard label="Tổng BN"       value={s.total}       icon="👥" color="var(--clr-primary)"   bg="var(--clr-primary-light)" />
          <StatCard label="Đang chờ"      value={s.waiting}     icon="⏳" color="#92400e" bg="#fef3c7" />
          <StatCard label="Đi CLS"        value={s.cls + s.cls_result} icon="🔬" color="#7c3aed" bg="#ede9fe" />
          <StatCard label="Đã khám xong"  value={s.done}        icon="✅" color="#065f46" bg="#d1fae5" />
        </div>
      )}

      {/* Queue list */}
      <Card title={`Hàng chờ khám — ${clinicRoom || 'Chưa chọn phòng'}`}>
        {!clinicRoom && <EmptyState icon="🏥" title="Chưa chọn phòng khám" description="Nhập tên phòng khám vào ô lọc phía trên." />}
        {clinicRoom && listAsync.loading && <LoadingOverlay />}
        {clinicRoom && !listAsync.loading && (listAsync.data?.length ?? 0) === 0 && (
          <EmptyState icon="🎉" title="Không có bệnh nhân chờ" description="Hàng đợi trống. Bệnh nhân mới sẽ hiện ngay khi check-in." />
        )}
        {(listAsync.data?.length ?? 0) > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(listAsync.data ?? []).map(item => (
              <PatientCard
                key={item.id}
                item={item}
                onVisitStatus={handleVisitStatus}
                onDone={() => setDoneTarget(item)}
                onTransfer={() => setTransferTarget(item)}
                onExamine={() => navigate(toPath(ROUTES.DOCTOR_PATIENT, { receptionId: item.id }))}
              />
            ))}
          </div>
        )}
      </Card>

      {/* Transfer modal */}
      {transferTarget && (
        <TransferModal
          reception={transferTarget}
          onClose={() => setTransferTarget(null)}
          onSuccess={() => { setTransferTarget(null); load(); }}
        />
      )}

      {/* Done confirm */}
      <ConfirmDialog
        open={!!doneTarget}
        onClose={() => setDoneTarget(null)}
        onConfirm={handleDone}
        title="Kết thúc khám"
        message={`Xác nhận hoàn tất lượt khám của bệnh nhân ${doneTarget?.patient.full_name ?? ''}?`}
        confirmLabel="Hoàn tất"
      />
    </div>
  );
}

// ── PatientCard ───────────────────────────────────────────────────────────────
interface CardProps {
  item:           QueueItem;
  onVisitStatus:  (id: number, s: VisitStatus) => void;
  onDone:         () => void;
  onTransfer:     () => void;
  onExamine:      () => void;
}

const VISIT_STATUS_ACTIONS: { label: string; status: VisitStatus; variant?: 'primary' | 'secondary' | 'ghost' }[] = [
  { label: 'Đi CLS',       status: 'cls',        variant: 'secondary' },
  { label: 'Có KQ CLS',    status: 'cls_result',  variant: 'secondary' },
  { label: 'Hẹn tái khám', status: 'revisit',    variant: 'ghost'    },
];

function PatientCard({ item, onVisitStatus, onDone, onTransfer, onExamine }: CardProps) {
  const p = item.patient;
  const priorityColor = item.priority >= 2 ? 'var(--clr-danger)' : item.priority === 1 ? 'var(--clr-warning)' : 'var(--clr-gray-300)';

  return (
    <div style={{
      background: '#fff', border: `2px solid ${item.priority >= 1 ? priorityColor : 'var(--clr-gray-100)'}`,
      borderRadius: 12, padding: '16px 20px',
      boxShadow: item.priority >= 1 ? `0 2px 12px ${priorityColor}30` : 'var(--shadow-sm)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        {/* Left: patient info */}
        <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start', flex: 1 }}>
          <div style={{
            minWidth: 48, height: 48, borderRadius: '50%',
            background: 'var(--clr-primary-light)', color: 'var(--clr-primary-dark)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: '1rem',
          }}>
            {item.visit_number ?? '?'}
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--clr-gray-800)' }}>
              {p.full_name}
              {item.priority >= 2 && <span style={{ marginLeft: 8, fontSize: '.75rem', background: 'var(--clr-danger)', color: '#fff', padding: '1px 8px', borderRadius: 9999 }}>CẤP CỨU</span>}
              {item.priority === 1 && <span style={{ marginLeft: 8, fontSize: '.75rem', background: 'var(--clr-warning)', color: '#fff', padding: '1px 8px', borderRadius: 9999 }}>ƯU TIÊN</span>}
            </div>
            <div className="flex gap-3 mt-1">
              <span className="text-xs text-muted">{fmtGender(p.gender)}</span>
              {p.birth_year && <span className="text-xs text-muted">{p.birth_year}</span>}
              {p.phone && <span className="text-xs text-muted">{p.phone}</span>}
              <span className="text-xs text-muted">{item.subject_name ?? '—'}</span>
            </div>
          </div>
        </div>

        {/* Right: status */}
        <StatusBadge status={item.visit_status} />
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-3" style={{ flexWrap: 'wrap' }}>
        <Button size="sm" onClick={onExamine}>🩺 Khám</Button>
        {VISIT_STATUS_ACTIONS.filter(a => a.status !== item.visit_status).map(a => (
          <Button key={a.status} size="sm" variant={a.variant ?? 'secondary'}
            onClick={() => onVisitStatus(item.id, a.status)}>
            {a.label}
          </Button>
        ))}
        <Button size="sm" variant="ghost" onClick={onTransfer}>🔄 Chuyển phòng</Button>
        <Button size="sm" variant="ghost" onClick={onDone} style={{ marginLeft: 'auto', color: 'var(--clr-success)' }}>
          ✅ Xong
        </Button>
      </div>
    </div>
  );
}

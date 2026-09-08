import { useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { doctorApi } from '@api/doctor.api';
import { useAuth } from '@features/auth/AuthContext';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatCard, EmptyState, LoadingOverlay, ConfirmDialog } from '@components/ui';
import { today, VISIT_STATUS_LABELS } from '@lib/utils';
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

const VISIT_STATUS_ACTIONS: { label: string; status: VisitStatus; icon: string }[] = [
  { label: 'Đi làm CLS',       status: 'cls',        icon: '🔬' },
  { label: 'Có kết quả CLS',   status: 'cls_result', icon: '📋' },
  { label: 'Hẹn tái khám',     status: 'revisit',    icon: '📅' },
  { label: 'Chờ khám lại',     status: 'waiting',    icon: '⏳' },
];

function PatientCard({ item, onVisitStatus, onDone, onTransfer, onExamine }: CardProps) {
  const p = item.patient;
  const [menuOpen, setMenuOpen] = useState(false);

  const priorityColor =
    item.priority >= 2 ? 'var(--clr-danger)'
    : item.priority === 1 ? 'var(--clr-warning)'
    : 'var(--clr-gray-200)';

  const visitStatusColor: Record<string, string> = {
    waiting:    '#1e40af',
    cls:        '#7c3aed',
    cls_result: '#ea580c',
    revisit:    '#0891b2',
    done:       '#065f46',
  };

  const visitStatusBg: Record<string, string> = {
    waiting:    '#dbeafe',
    cls:        '#ede9fe',
    cls_result: '#ffedd5',
    revisit:    '#cffafe',
    done:       '#d1fae5',
  };

  const vsColor = visitStatusColor[item.visit_status] ?? 'var(--clr-gray-600)';
  const vsBg    = visitStatusBg[item.visit_status]    ?? 'var(--clr-gray-100)';

  return (
    <div
      style={{
        background: '#fff',
        border: `2px solid ${item.priority >= 1 ? priorityColor : 'var(--clr-gray-100)'}`,
        borderRadius: 14,
        boxShadow: item.priority >= 1 ? `0 2px 12px ${priorityColor}30` : 'var(--shadow-sm)',
        overflow: 'visible',
        position: 'relative',
        transition: 'box-shadow .15s, border-color .15s',
        cursor: 'pointer',
      }}
      onClick={onExamine}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'var(--shadow-lg)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = item.priority >= 1 ? `0 2px 12px ${priorityColor}30` : 'var(--shadow-sm)'; }}
    >
      {/* ── Top section — clickable ──────────────────────────── */}
      <div style={{ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 14 }}>

        {/* Number badge */}
        <div style={{
          minWidth: 52, height: 52, borderRadius: 14,
          background: 'linear-gradient(135deg, var(--clr-primary-light), #bae6fd)',
          color: 'var(--clr-primary-dark)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 900, fontSize: '1.3rem', flexShrink: 0,
          border: '2px solid var(--clr-primary-light)',
        }}>
          {item.visit_number ?? '?'}
        </div>

        {/* Patient info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
            <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--clr-gray-900)' }}>
              {p.full_name}
            </span>
            {item.priority >= 2 && (
              <span style={{ fontSize: '.7rem', background: 'var(--clr-danger)', color: '#fff', padding: '2px 8px', borderRadius: 9999, fontWeight: 700 }}>
                🚨 CẤP CỨU
              </span>
            )}
            {item.priority === 1 && (
              <span style={{ fontSize: '.7rem', background: 'var(--clr-warning)', color: '#fff', padding: '2px 8px', borderRadius: 9999, fontWeight: 700 }}>
                ⚡ ƯU TIÊN
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {p.birth_year && <span className="text-xs text-muted">🎂 {p.birth_year}</span>}
            {p.gender && <span className="text-xs text-muted">{p.gender === 'male' ? '♂ Nam' : '♀ Nữ'}</span>}
            {p.phone && <span className="text-xs text-muted">📞 {p.phone}</span>}
            {item.subject_name && <span className="text-xs" style={{ color: 'var(--clr-primary-dark)', fontWeight: 500 }}>🏥 {item.subject_name}</span>}
            {item.visit_time && <span className="text-xs text-muted">⏰ {item.visit_time}</span>}
          </div>
        </div>

        {/* Visit status pill */}
        <div style={{
          padding: '5px 14px', borderRadius: 9999, fontSize: '.78rem', fontWeight: 700,
          background: vsBg, color: vsColor, flexShrink: 0,
          border: `1px solid ${vsColor}30`,
        }}>
          {({ waiting: '⏳ Chờ khám', cls: '🔬 Đi CLS', cls_result: '📋 Có KQ CLS', revisit: '📅 Tái khám', done: '✅ Xong' } as Record<string, string>)[item.visit_status] ?? item.visit_status}
        </div>

        {/* Caret hint */}
        <span style={{ color: 'var(--clr-gray-300)', fontSize: '1.1rem', flexShrink: 0 }}>›</span>
      </div>

      {/* ── Action bar — stop propagation ────────────────────── */}
      <div
        style={{
          padding: '10px 16px',
          background: 'var(--clr-gray-50)',
          borderTop: '1px solid var(--clr-gray-100)',
          display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Primary action */}
        <button
          onClick={onExamine}
          style={{
            padding: '6px 18px', borderRadius: 8, border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg, var(--clr-primary), var(--clr-primary-dark))',
            color: '#fff', fontWeight: 700, fontSize: '.85rem', fontFamily: 'var(--font-sans)',
            boxShadow: '0 2px 8px rgba(14,165,233,.3)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          🩺 Mở phiếu khám
        </button>

        {/* Status change buttons */}
        {VISIT_STATUS_ACTIONS
          .filter(a => a.status !== item.visit_status)
          .map(a => (
            <button
              key={a.status}
              onClick={() => onVisitStatus(item.id, a.status)}
              style={{
                padding: '6px 14px', borderRadius: 8, fontSize: '.82rem',
                border: '1.5px solid var(--clr-gray-200)',
                background: '#fff', cursor: 'pointer', fontFamily: 'var(--font-sans)',
                color: 'var(--clr-gray-700)', fontWeight: 500,
                display: 'flex', alignItems: 'center', gap: 5,
                transition: 'background .15s, border-color .15s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--clr-gray-100)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = '#fff'; }}
            >
              {a.icon} {a.label}
            </button>
          ))
        }

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Transfer */}
        <button
          onClick={onTransfer}
          style={{
            padding: '6px 14px', borderRadius: 8, fontSize: '.82rem',
            border: '1.5px solid var(--clr-gray-200)',
            background: '#fff', cursor: 'pointer', fontFamily: 'var(--font-sans)',
            color: 'var(--clr-gray-600)', fontWeight: 500,
          }}
        >
          🔄 Chuyển phòng
        </button>

        {/* Done */}
        <button
          onClick={onDone}
          style={{
            padding: '6px 14px', borderRadius: 8, fontSize: '.82rem',
            border: '1.5px solid #86efac',
            background: '#f0fdf4', cursor: 'pointer', fontFamily: 'var(--font-sans)',
            color: '#166534', fontWeight: 700,
          }}
        >
          ✅ Hoàn thành
        </button>
      </div>
    </div>
  );
}

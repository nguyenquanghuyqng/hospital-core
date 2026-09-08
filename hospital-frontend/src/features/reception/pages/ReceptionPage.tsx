/**
 * ReceptionPage — Quầy tiếp đón bệnh nhân.
 *
 * Layout split-panel:
 * ┌─────────────────┬────────────────────────────────────────┐
 * │  Panel trái     │  Panel phải                            │
 * │  - Quét CCCD    │  - Stats hôm nay                       │
 * │  - Đăng ký nhanh│  - Danh sách bệnh nhân (realtime WS)   │
 * │  - Thống kê     │  - Filter + Pagination                  │
 * │    phòng        │  - Actions: check-in / huỷ inline       │
 * └─────────────────┴────────────────────────────────────────┘
 *
 * Ít thao tác nhất có thể:
 * - Quét CCCD → tự điền form → 1 click đăng ký
 * - Check-in ngay từ dòng table (không cần mở modal riêng)
 * - Badge màu trạng thái rõ ràng
 */
import { useEffect, useCallback, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { receptionApi } from '@api/reception.api';
import { patientApi } from '@api/patient.api';
import { useReceptionStore } from '@store/reception.store';
import { useAsync } from '@hooks/useAsync';
import { usePagination } from '@hooks/usePagination';
import { useWebSocket } from '@hooks/useWebSocket';
import {
  Button, StatusBadge, EmptyState, ErrorState,
  LoadingOverlay, Pagination, ConfirmDialog, Modal, Field,
} from '@components/ui';
import { fmtDate, today } from '@lib/utils';
import { ROUTES, toPath } from '@/app/routes';
import type { PatientResponse, ReceptionList } from '@/types';

// ── Constants ─────────────────────────────────────────────────────────────────
const CLINIC_ROOMS = ['Phòng 1', 'Phòng 2', 'Phòng 3', 'Phòng 4', 'Phòng Tim Mạch', 'Phòng Nhi', 'Phòng Da Liễu'];
const SUBJECT_TYPES = [
  { value: '1', label: 'BHYT' },
  { value: '2', label: 'Dịch vụ' },
  { value: '3', label: 'Miễn phí' },
  { value: '4', label: 'Theo yêu cầu' },
];

// ─────────────────────────────────────────────────────────────────────────────
export default function ReceptionPage() {
  const navigate    = useNavigate();
  const store       = useReceptionStore();
  const listAsync   = useAsync<{ items: ReceptionList[]; total: number; total_pages: number }>();
  const statsAsync  = useAsync<Record<string, number>>();
  const { page, pageSize, goTo } = usePagination({ initialPageSize: 25 });

  const [cancelTarget,  setCancelTarget]  = useState<ReceptionList | null>(null);
  const [checkInTarget, setCheckInTarget] = useState<ReceptionList | null>(null);
  const [filterStatus,  setFilterStatus]  = useState('');
  const [filterDate,    setFilterDate]    = useState(today());
  const cancelAsync  = useAsync<unknown>();
  const checkInAsync = useAsync<unknown>();

  // ── Load ──────────────────────────────────────────────────────────────────
  const load = useCallback(() => {
    listAsync.run(
      receptionApi.list({
        visit_date: filterDate,
        status:     filterStatus || undefined,
        page, page_size: pageSize,
      }) as Promise<{ items: ReceptionList[]; total: number; total_pages: number }>,
    ).then(res => { if (res) store.setList(res.items, res.total); });

    statsAsync.run(receptionApi.stats() as Promise<Record<string, number>>);
  }, [filterDate, filterStatus, page, pageSize]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load(); }, [load]);

  // ── WebSocket realtime ────────────────────────────────────────────────────
  useWebSocket({
    room: 'reception',
    onMessage: (type) => {
      if (['reception_update', 'reception_created', 'reception_updated', 'doctor_queue_update'].includes(type)) {
        load();
      }
    },
  });

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleQuickCheckIn = async (r: ReceptionList) => {
    const res = await checkInAsync.run(receptionApi.checkIn(r.id, {}));
    if (res !== null) { toast.success(`✅ Check-in: ${r.patient?.full_name}`); load(); }
    else toast.error(checkInAsync.error ?? 'Thất bại');
  };

  const handleCancel = async () => {
    if (!cancelTarget) return;
    const res = await cancelAsync.run(receptionApi.cancel(cancelTarget.id));
    if (res !== null) { toast.success('Đã huỷ'); load(); }
    else toast.error(cancelAsync.error ?? 'Thất bại');
    setCancelTarget(null);
  };

  const s = statsAsync.data;

  return (
    <div style={{ display: 'flex', gap: 0, minHeight: 'calc(100vh - var(--header-h))', padding: 0 }}>

      {/* ══ LEFT PANEL — đăng ký + stats ══════════════════════════════════ */}
      <div style={{
        width: 340, flexShrink: 0,
        borderRight: '1px solid var(--clr-gray-100)',
        background: '#fff',
        display: 'flex', flexDirection: 'column',
        overflowY: 'auto',
      }}>

        {/* Stats hôm nay */}
        <div style={{ padding: '18px 18px 0' }}>
          <div style={{ fontSize: '.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--clr-gray-400)', marginBottom: 12 }}>
            HÔM NAY
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {[
              { label: 'Tổng',        value: s?.total       ?? 0, color: '#0284c7', bg: '#e0f2fe' },
              { label: 'Chờ',         value: s?.pending     ?? 0, color: '#92400e', bg: '#fef3c7' },
              { label: 'Đã tiếp nhận',value: s?.checked_in  ?? 0, color: '#1e40af', bg: '#dbeafe' },
              { label: 'Hoàn thành',  value: s?.completed   ?? 0, color: '#065f46', bg: '#d1fae5' },
            ].map(item => (
              <div key={item.label} style={{
                padding: '12px 14px', borderRadius: 10,
                background: item.bg, cursor: 'default',
              }}>
                <div style={{ fontSize: '1.6rem', fontWeight: 800, color: item.color, lineHeight: 1 }}>
                  {item.value}
                </div>
                <div style={{ fontSize: '.8rem', color: item.color, opacity: .8, marginTop: 3 }}>
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div style={{ margin: '18px 0 0', height: 1, background: 'var(--clr-gray-100)' }} />

        {/* Đăng ký nhanh */}
        <RegisterPanel onSuccess={load} />
      </div>

      {/* ══ RIGHT PANEL — danh sách ══════════════════════════════════════ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Toolbar */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--clr-gray-100)',
          display: 'flex', gap: 10, alignItems: 'center',
          background: '#fff', flexWrap: 'wrap',
        }}>
          <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--clr-gray-800)', flex: 1 }}>
            Danh sách tiếp đón
            {store.total > 0 && (
              <span style={{ marginLeft: 8, fontSize: '.8rem', fontWeight: 400, color: 'var(--clr-gray-500)' }}>
                ({store.total} lượt)
              </span>
            )}
          </span>

          <input type="date" className="form-input"
            style={{ width: 150 }}
            value={filterDate}
            onChange={e => { setFilterDate(e.target.value); goTo(1); }}
          />
          <select className="form-input" style={{ width: 160 }}
            value={filterStatus}
            onChange={e => { setFilterStatus(e.target.value); goTo(1); }}
          >
            <option value="">Tất cả trạng thái</option>
            <option value="pending">⏳ Chờ tiếp nhận</option>
            <option value="checked_in">✅ Đã tiếp nhận</option>
            <option value="completed">🏁 Hoàn thành</option>
            <option value="cancelled">❌ Đã huỷ</option>
          </select>
          <Button size="sm" variant="ghost" onClick={load}>↻</Button>
        </div>

        {/* Table */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px' }}>
          {listAsync.loading && <LoadingOverlay />}
          {listAsync.error   && <ErrorState message={listAsync.error} onRetry={load} />}
          {!listAsync.loading && !listAsync.error && store.list.length === 0 && (
            <EmptyState icon="📋" title="Chưa có lượt tiếp đón"
              description="Dùng form bên trái để đăng ký lượt khám mới." />
          )}
          {!listAsync.loading && store.list.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.9375rem' }}>
              <thead>
                <tr style={{ background: 'var(--clr-gray-50)', position: 'sticky', top: 0, zIndex: 1 }}>
                  <th style={thStyle}>STT</th>
                  <th style={thStyle}>Bệnh nhân</th>
                  <th style={thStyle}>Giờ</th>
                  <th style={thStyle}>Phòng</th>
                  <th style={thStyle}>Đối tượng</th>
                  <th style={thStyle}>Trạng thái</th>
                  <th style={{ ...thStyle, width: 160 }}>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {store.list.map(r => (
                  <tr key={r.id} style={{ borderBottom: '1px solid var(--clr-gray-50)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--clr-gray-50)')}
                    onMouseLeave={e => (e.currentTarget.style.background = '#fff')}
                  >
                    {/* STT */}
                    <td style={tdStyle}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 8,
                        background: r.priority >= 2 ? '#fee2e2' : r.priority === 1 ? '#fef3c7' : 'var(--clr-primary-light)',
                        color:      r.priority >= 2 ? '#991b1b' : r.priority === 1 ? '#92400e' : 'var(--clr-primary-dark)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontWeight: 800, fontSize: '.95rem',
                      }}>
                        {r.visit_number ?? '—'}
                      </div>
                    </td>

                    {/* Bệnh nhân */}
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600, color: 'var(--clr-gray-900)', lineHeight: 1.3 }}>
                        {r.patient?.full_name ?? '—'}
                      </div>
                      <div style={{ fontSize: '.8125rem', color: 'var(--clr-gray-400)', marginTop: 2 }}>
                        {r.patient?.cccd ?? r.patient?.phone ?? ''}
                      </div>
                    </td>

                    {/* Giờ */}
                    <td style={{ ...tdStyle, color: 'var(--clr-gray-500)', fontSize: '.875rem' }}>
                      {r.visit_time ?? fmtDate(r.visit_date)}
                    </td>

                    {/* Phòng */}
                    <td style={{ ...tdStyle, fontSize: '.875rem', fontWeight: 500 }}>
                      {r.clinic_room ?? '—'}
                    </td>

                    {/* Đối tượng */}
                    <td style={{ ...tdStyle }}>
                      {r.subject_name ? (
                        <span style={{
                          fontSize: '.8125rem', fontWeight: 600, padding: '2px 10px',
                          borderRadius: 9999, background: r.subject_name.includes('BHYT') ? '#dbeafe' : '#f3e8ff',
                          color: r.subject_name.includes('BHYT') ? '#1e40af' : '#6b21a8',
                        }}>
                          {r.subject_name}
                        </span>
                      ) : <span style={{ color: 'var(--clr-gray-300)' }}>—</span>}
                    </td>

                    {/* Trạng thái */}
                    <td style={tdStyle}><StatusBadge status={r.status} /></td>

                    {/* Thao tác */}
                    <td style={{ ...tdStyle, whiteSpace: 'nowrap' }}>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          onClick={() => navigate(toPath(ROUTES.RECEPTION_DETAIL, { id: r.id }))}
                          style={actionBtnStyle}
                          title="Xem chi tiết"
                        >
                          👁
                        </button>
                        {r.status === 'pending' && (
                          <button
                            onClick={() => setCheckInTarget(r)}
                            style={{ ...actionBtnStyle, background: '#dbeafe', color: '#1e40af' }}
                            title="Check-in nhanh"
                          >
                            ✅ Check-in
                          </button>
                        )}
                        {r.status === 'checked_in' && (
                          <button
                            onClick={() => navigate(toPath(ROUTES.RECEPTION_DETAIL, { id: r.id }))}
                            style={{ ...actionBtnStyle, background: '#d1fae5', color: '#065f46' }}
                            title="Mở phiếu khám"
                          >
                            🩺
                          </button>
                        )}
                        {(r.status === 'pending' || r.status === 'checked_in') && (
                          <button
                            onClick={() => setCancelTarget(r)}
                            style={{ ...actionBtnStyle, background: '#fee2e2', color: '#991b1b' }}
                            title="Huỷ lượt"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {(listAsync.data?.total_pages ?? 0) > 1 && (
          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--clr-gray-100)',
            display: 'flex', justifyContent: 'flex-end', background: '#fff',
          }}>
            <Pagination page={page} totalPages={listAsync.data?.total_pages ?? 1} onChange={goTo} />
          </div>
        )}
      </div>

      {/* ── Modals ────────────────────────────────────────────────────── */}
      {checkInTarget && (
        <CheckInQuickModal
          reception={checkInTarget}
          onClose={() => setCheckInTarget(null)}
          onQuick={() => { handleQuickCheckIn(checkInTarget); setCheckInTarget(null); }}
          onSuccess={() => { setCheckInTarget(null); load(); }}
        />
      )}

      <ConfirmDialog
        open={!!cancelTarget}
        onClose={() => setCancelTarget(null)}
        onConfirm={handleCancel}
        title="Huỷ lượt tiếp đón"
        message={`Xác nhận huỷ lượt khám của ${cancelTarget?.patient?.full_name ?? 'bệnh nhân này'}?`}
        confirmLabel="Huỷ lượt"
        danger
      />
    </div>
  );
}

// ── CSS-in-JS helpers ─────────────────────────────────────────────────────────
const thStyle: React.CSSProperties = {
  padding: '10px 14px', textAlign: 'left', fontSize: '.8125rem',
  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em',
  color: 'var(--clr-gray-500)', borderBottom: '2px solid var(--clr-gray-100)',
  whiteSpace: 'nowrap', background: 'var(--clr-gray-50)',
};
const tdStyle: React.CSSProperties = {
  padding: '12px 14px', verticalAlign: 'middle',
};
const actionBtnStyle: React.CSSProperties = {
  padding: '5px 10px', borderRadius: 7, border: 'none',
  background: 'var(--clr-gray-100)', color: 'var(--clr-gray-600)',
  cursor: 'pointer', fontSize: '.8125rem', fontWeight: 600,
  fontFamily: 'var(--font-sans)', transition: 'opacity .15s',
  display: 'inline-flex', alignItems: 'center', gap: 4,
};

// ─────────────────────────────────────────────────────────────────────────────
// RegisterPanel — panel đăng ký nhanh bên trái
// ─────────────────────────────────────────────────────────────────────────────
interface RegisterPanelProps { onSuccess: () => void }

function RegisterPanel({ onSuccess }: RegisterPanelProps) {
  const [cccd,        setCccd]        = useState('');
  const [fullName,    setFullName]    = useState('');
  const [birthYear,   setBirthYear]   = useState('');
  const [gender,      setGender]      = useState('');
  const [phone,       setPhone]       = useState('');
  const [clinicRoom,  setClinicRoom]  = useState('');
  const [subjectType, setSubjectType] = useState('1');
  const [insuranceNo, setInsuranceNo] = useState('');
  const [priority,    setPriority]    = useState('0');
  const [reason,      setReason]      = useState('');
  const [foundPatient, setFoundPatient] = useState<PatientResponse | null>(null);

  const scanAsync   = useAsync<unknown>();
  const createAsync = useAsync<unknown>();
  const cccdRef = useRef<HTMLInputElement>(null);

  const resetForm = () => {
    setCccd(''); setFullName(''); setBirthYear(''); setGender('');
    setPhone(''); setInsuranceNo(''); setReason(''); setPriority('0');
    setFoundPatient(null);
  };

  // Quét CCCD — auto lookup
  const handleScanCccd = async () => {
    if (!cccd || cccd.length < 9) return;
    const res = await scanAsync.run(
      receptionApi.scanCccd({ cccd }) as unknown as Promise<{ patient: PatientResponse; is_new_patient: boolean; message: string }>,
    );
    if (res) {
      const r = res as { patient: PatientResponse; is_new_patient: boolean; message: string };
      setFoundPatient(r.patient);
      setFullName(r.patient.full_name);
      setBirthYear(String(r.patient.birth_year ?? ''));
      setGender(r.patient.gender ?? '');
      setPhone(r.patient.phone ?? '');
      if (r.is_new_patient) toast('👤 Bệnh nhân mới — đã thêm', { icon: '✨' });
      else toast.success(`Tìm thấy: ${r.patient.full_name}`);
    } else {
      // CCCD chưa có → cho nhập tay
      toast('Chưa có trong hệ thống — vui lòng nhập thông tin', { icon: 'ℹ️' });
    }
  };

  // Tìm bệnh nhân bằng tên nếu không có CCCD
  const handleSearchByName = async () => {
    if (!fullName.trim() || fullName.length < 2) return;
    const res = await scanAsync.run(
      patientApi.list({ search: fullName, page: 1, page_size: 1 }) as unknown as Promise<{ items: PatientResponse[] }>,
    );
    if (res) {
      const list = (res as { items: PatientResponse[] }).items;
      if (list.length > 0 && list[0]) {
        const p = list[0];
        setFoundPatient(p);
        setFullName(p.full_name);
        setBirthYear(String(p.birth_year ?? ''));
        setGender(p.gender ?? '');
        setPhone(p.phone ?? '');
        toast.success(`Tìm thấy: ${p.full_name}`);
      }
    }
  };

  const handleRegister = async () => {
    if (!fullName.trim()) { toast.error('Vui lòng nhập họ tên'); return; }
    if (!clinicRoom)       { toast.error('Vui lòng chọn phòng khám'); return; }

    const payload = {
      patient_id:       foundPatient?.id ?? undefined,
      patient_data:     foundPatient ? undefined : {
        full_name:  fullName,
        birth_year: birthYear ? Number(birthYear) : undefined,
        gender:     (gender as 'male' | 'female') || undefined,
        phone:      phone || undefined,
        cccd:       cccd || undefined,
      },
      clinic_room:      clinicRoom,
      subject_type:     subjectType || undefined,
      subject_name:     SUBJECT_TYPES.find(s => s.value === subjectType)?.label,
      insurance_number: insuranceNo || undefined,
      priority:         Number(priority),
      reason:           reason || undefined,
    };

    const res = await createAsync.run(receptionApi.create(payload));
    if (res !== null) {
      toast.success('🎉 Đăng ký thành công!');
      resetForm();
      onSuccess();
      cccdRef.current?.focus();
    } else {
      toast.error(createAsync.error ?? 'Đăng ký thất bại');
    }
  };

  return (
    <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14, flex: 1 }}>

      <div style={{ fontSize: '.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--clr-gray-400)' }}>
        ĐĂNG KÝ NHANH
      </div>

      {/* CCCD scan */}
      <div>
        <label style={labelStyle}>Quét CCCD / CMND</label>
        <div style={{ display: 'flex', gap: 6, marginTop: 5 }}>
          <input
            ref={cccdRef}
            className="form-input"
            value={cccd}
            onChange={e => setCccd(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleScanCccd()}
            placeholder="Quét thẻ hoặc nhập số..."
            autoFocus
          />
          <button onClick={handleScanCccd} disabled={scanAsync.loading}
            style={{ ...actionBtnStyle, background: 'var(--clr-primary)', color: '#fff', padding: '8px 14px', flexShrink: 0 }}>
            {scanAsync.loading ? '...' : '🔍'}
          </button>
        </div>
        {foundPatient && (
          <div style={{
            marginTop: 6, padding: '6px 10px', borderRadius: 7,
            background: '#d1fae5', fontSize: '.8125rem', color: '#065f46',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>✓</span>
            <span style={{ fontWeight: 600 }}>{foundPatient.full_name}</span>
            <button onClick={resetForm}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#065f46', fontSize: '.85rem' }}>
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Họ tên */}
      <div>
        <label style={labelStyle}>Họ và tên <span style={{ color: 'var(--clr-danger)' }}>*</span></label>
        <div style={{ display: 'flex', gap: 6, marginTop: 5 }}>
          <input className="form-input" value={fullName}
            onChange={e => setFullName(e.target.value)}
            onBlur={!foundPatient ? handleSearchByName : undefined}
            placeholder="Nguyễn Văn A"
            readOnly={!!foundPatient}
          />
        </div>
      </div>

      {/* Năm sinh + Giới tính */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div>
          <label style={labelStyle}>Năm sinh</label>
          <input className="form-input" style={{ marginTop: 5 }} value={birthYear}
            type="number" min={1920} max={2024}
            onChange={e => setBirthYear(e.target.value)} placeholder="1990"
            readOnly={!!foundPatient} />
        </div>
        <div>
          <label style={labelStyle}>Giới tính</label>
          <select className="form-input" style={{ marginTop: 5 }} value={gender}
            onChange={e => setGender(e.target.value)} disabled={!!foundPatient}>
            <option value="">—</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
          </select>
        </div>
      </div>

      {/* SĐT */}
      <div>
        <label style={labelStyle}>Số điện thoại</label>
        <input className="form-input" style={{ marginTop: 5 }} value={phone}
          onChange={e => setPhone(e.target.value)} placeholder="0912 345 678"
          readOnly={!!foundPatient} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'var(--clr-gray-100)' }} />

      {/* Phòng khám */}
      <div>
        <label style={labelStyle}>Phòng khám <span style={{ color: 'var(--clr-danger)' }}>*</span></label>
        <select className="form-input" style={{ marginTop: 5 }} value={clinicRoom}
          onChange={e => setClinicRoom(e.target.value)}>
          <option value="">— Chọn phòng —</option>
          {CLINIC_ROOMS.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {/* Đối tượng + Ưu tiên */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div>
          <label style={labelStyle}>Đối tượng</label>
          <select className="form-input" style={{ marginTop: 5 }} value={subjectType}
            onChange={e => setSubjectType(e.target.value)}>
            {SUBJECT_TYPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label style={labelStyle}>Ưu tiên</label>
          <select className="form-input" style={{ marginTop: 5 }} value={priority}
            onChange={e => setPriority(e.target.value)}>
            <option value="0">Thường</option>
            <option value="1">⚡ Ưu tiên</option>
            <option value="2">🚨 Cấp cứu</option>
          </select>
        </div>
      </div>

      {/* BHYT */}
      {subjectType === '1' && (
        <div>
          <label style={labelStyle}>Số thẻ BHYT</label>
          <input className="form-input" style={{ marginTop: 5 }} value={insuranceNo}
            onChange={e => setInsuranceNo(e.target.value)} placeholder="DN4012345678" />
        </div>
      )}

      {/* Lý do */}
      <div>
        <label style={labelStyle}>Lý do khám</label>
        <textarea className="form-input" style={{ marginTop: 5 }} value={reason}
          onChange={e => setReason(e.target.value)}
          rows={2} placeholder="Triệu chứng, lý do đến khám..." />
      </div>

      {/* Submit */}
      <button
        onClick={handleRegister}
        disabled={createAsync.loading || !fullName.trim() || !clinicRoom}
        style={{
          width: '100%', padding: '13px',
          background: 'linear-gradient(135deg, var(--clr-primary), var(--clr-primary-dark))',
          color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer',
          fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--font-sans)',
          opacity: (!fullName.trim() || !clinicRoom) ? .5 : 1,
          boxShadow: '0 3px 10px rgba(14,165,233,.35)',
          transition: 'opacity .15s',
          marginTop: 4,
        }}
      >
        {createAsync.loading ? '⏳ Đang đăng ký...' : '✅ Đăng ký lượt khám'}
      </button>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: '.875rem', fontWeight: 600, color: 'var(--clr-gray-600)',
};

// ─────────────────────────────────────────────────────────────────────────────
// CheckInQuickModal — check-in với option thêm thông tin
// ─────────────────────────────────────────────────────────────────────────────
interface CheckInQuickModalProps {
  reception: ReceptionList;
  onClose:   () => void;
  onQuick:   () => void;
  onSuccess: () => void;
}

function CheckInQuickModal({ reception, onClose, onQuick, onSuccess }: CheckInQuickModalProps) {
  const [receptionistName, setReceptionistName] = useState('');
  const [note,             setNote]             = useState('');
  const checkInAsync = useAsync<unknown>();

  const handleFull = async () => {
    const res = await checkInAsync.run(
      receptionApi.checkIn(reception.id, {
        receptionist_name: receptionistName || null,
        internal_note:     note || null,
      }),
    );
    if (res !== null) {
      toast.success(`✅ Check-in: ${reception.patient?.full_name}`);
      onSuccess();
    } else toast.error(checkInAsync.error ?? 'Thất bại');
  };

  return (
    <Modal open onClose={onClose} title={`Check-in — ${reception.patient?.full_name ?? ''}`} size="sm"
      footer={
        <div style={{ display: 'flex', gap: 8, width: '100%' }}>
          <Button variant="ghost" onClick={onClose} style={{ flex: 1 }}>Huỷ</Button>
          <Button variant="secondary" onClick={onQuick} style={{ flex: 1 }}>⚡ Nhanh</Button>
          <Button loading={checkInAsync.loading} onClick={handleFull} style={{ flex: 1 }}>✅ Check-in</Button>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ padding: '10px 14px', background: 'var(--clr-gray-50)', borderRadius: 8, fontSize: '.875rem' }}>
          <div><strong>Phòng:</strong> {reception.clinic_room ?? '—'}</div>
          <div><strong>Số khám:</strong> {reception.visit_number ?? '—'}</div>
          <div><strong>Đối tượng:</strong> {reception.subject_name ?? '—'}</div>
        </div>
        <Field label="Nhân viên tiếp đón">
          <input className="form-input" value={receptionistName}
            onChange={e => setReceptionistName(e.target.value)} placeholder="Họ tên nhân viên" autoFocus />
        </Field>
        <Field label="Ghi chú nội bộ">
          <textarea className="form-input" rows={2} value={note}
            onChange={e => setNote(e.target.value)} placeholder="Ghi chú cho bác sĩ..." />
        </Field>
        <p style={{ fontSize: '.8125rem', color: 'var(--clr-gray-400)' }}>
          Hoặc nhấn <strong>⚡ Nhanh</strong> để check-in ngay không cần điền thêm.
        </p>
      </div>
    </Modal>
  );
}

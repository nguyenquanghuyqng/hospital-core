/**
 * ExaminationPage — Phiếu khám bệnh đầy đủ chức năng bác sĩ.
 *
 * Layout: Header cố định (thông tin BN + actions) + Tab navigation + Tab content
 *
 * Tabs:
 *  1. Khám bệnh      — triệu chứng, chẩn đoán, dấu hiệu sinh tồn
 *  2. Đơn thuốc      — BHYT + ngoài BHYT tách biệt
 *  3. Chỉ định CLS   — danh sách chỉ định + cập nhật kết quả
 *  4. Tạm ứng        — chỉ định tạm ứng viện phí
 *  5. Hẹn khám       — phiếu hẹn tái khám
 *  6. Giấy BHXH      — giấy nghỉ hưởng BHXH
 *  7. Chi phí         — tổng hợp chi phí
 */
import { useEffect, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { examinationApi } from '@api/examination.api';
import { receptionApi } from '@api/reception.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatusBadge, LoadingOverlay, ErrorState, ConfirmDialog, Field } from '@components/ui';
import { fmtDate, fmtDateTime } from '@lib/utils';
import { ROUTES } from '@/app/routes';
import type { ExaminationResponse, ReceptionResponse } from '@/types';
import DiagnosisPanel from '../components/DiagnosisPanel';
import PrescriptionPanel from '../components/PrescriptionPanel';
import ClsPanel from '../components/ClsPanel';

// ── Tab definitions ────────────────────────────────────────────────────────────
type TabId = 'exam' | 'prescription' | 'cls' | 'deposit' | 'appointment' | 'bhxh' | 'cost';

interface Tab { id: TabId; icon: string; label: string }

const TABS: Tab[] = [
  { id: 'exam',        icon: '🩺', label: 'Khám bệnh'     },
  { id: 'prescription',icon: '💊', label: 'Đơn thuốc'     },
  { id: 'cls',         icon: '🔬', label: 'Chỉ định CLS'  },
  { id: 'deposit',     icon: '💰', label: 'Tạm ứng'       },
  { id: 'appointment', icon: '📅', label: 'Hẹn khám'      },
  { id: 'bhxh',        icon: '📄', label: 'Giấy BHXH'     },
  { id: 'cost',        icon: '🧾', label: 'Chi phí'        },
];

// ── Main component ─────────────────────────────────────────────────────────────
export default function ExaminationPage() {
  const { receptionId } = useParams<{ receptionId: string }>();
  const navigate = useNavigate();

  const receptionAsync   = useAsync<ReceptionResponse>();
  const examinationAsync = useAsync<ExaminationResponse>();
  const actionAsync      = useAsync<ExaminationResponse>();

  const [activeTab,       setActiveTab]       = useState<TabId>('exam');
  const [confirmComplete, setConfirmComplete] = useState(false);

  // ── Load / create ──────────────────────────────────────────────────────────
  const loadOrCreate = useCallback(async () => {
    if (!receptionId) return;
    const rid = Number(receptionId);
    await receptionAsync.run(receptionApi.get(rid));
    let exam = await examinationAsync.run(
      examinationApi.getByReception(rid).catch(() => null as unknown as ExaminationResponse),
    );
    if (!exam) {
      exam = await examinationAsync.run(examinationApi.create({ reception_id: rid }));
    }
  }, [receptionId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { void loadOrCreate(); }, [loadOrCreate]);

  const reload = useCallback(() => {
    if (receptionId) examinationAsync.run(examinationApi.getByReception(Number(receptionId)));
  }, [receptionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Actions ────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!examinationAsync.data) return;
    const res = await actionAsync.run(examinationApi.save(examinationAsync.data.id));
    if (res) { toast.success('Đã lưu phiếu khám'); reload(); }
    else toast.error(actionAsync.error ?? 'Lưu thất bại');
  };

  const handleComplete = async () => {
    if (!examinationAsync.data) return;
    const res = await actionAsync.run(examinationApi.complete(examinationAsync.data.id));
    if (res) { toast.success('Đã kết thúc khám!'); navigate(ROUTES.DOCTOR); }
    else toast.error(actionAsync.error ?? 'Thất bại');
  };

  // ── Guards ─────────────────────────────────────────────────────────────────
  if (receptionAsync.loading || examinationAsync.loading) return <LoadingOverlay />;
  if (examinationAsync.error) return <ErrorState message={examinationAsync.error} onRetry={loadOrCreate} />;
  const exam = examinationAsync.data;
  const rec  = receptionAsync.data;
  if (!exam) return null;

  const isCompleted = exam.status === 'completed';
  const p = rec?.patient;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: 'var(--clr-gray-50)' }}>

      {/* ── Sticky header ─────────────────────────────────────────────────── */}
      <div style={{
        position: 'sticky', top: 'var(--header-h)', zIndex: 50,
        background: '#fff', borderBottom: '1px solid var(--clr-gray-100)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        {/* Patient bar */}
        <div style={{ padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>←</Button>

          {/* Patient info compact */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
            <div style={{
              width: 40, height: 40, borderRadius: '50%', background: 'var(--clr-primary-light)',
              color: 'var(--clr-primary-dark)', display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontWeight: 800, fontSize: '.95rem', flexShrink: 0,
            }}>
              {(p?.full_name ?? '?')[0]}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--clr-gray-900)' }} className="truncate">
                {p?.full_name ?? `BN #${exam.patient_id}`}
              </div>
              <div className="flex gap-3">
                <span className="text-xs text-muted">{p?.birth_year ?? '—'}</span>
                <span className="text-xs text-muted">{p?.gender === 'male' ? 'Nam' : p?.gender === 'female' ? 'Nữ' : '—'}</span>
                {rec?.clinic_room && <span className="text-xs text-muted">📍 {rec.clinic_room}</span>}
                {rec?.subject_name && <span className="text-xs" style={{ color: 'var(--clr-primary-dark)' }}>🏥 {rec.subject_name}</span>}
                {exam.insurance_number && <span className="text-xs text-muted">🎫 {exam.insurance_number}</span>}
              </div>
            </div>
          </div>

          <StatusBadge status={exam.status} />

          {!isCompleted && (
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" loading={actionAsync.loading} onClick={handleSave}>
                💾 Lưu tạm
              </Button>
              <Button size="sm" onClick={() => setConfirmComplete(true)}>
                ✅ Kết thúc khám
              </Button>
            </div>
          )}
        </div>

        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 0, overflowX: 'auto', padding: '0 24px' }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '10px 16px',
                border: 'none', background: 'transparent', cursor: 'pointer',
                fontFamily: 'var(--font-sans)', fontSize: '.85rem', fontWeight: 500,
                color: activeTab === tab.id ? 'var(--clr-primary)' : 'var(--clr-gray-500)',
                borderBottom: `2px solid ${activeTab === tab.id ? 'var(--clr-primary)' : 'transparent'}`,
                transition: 'all .15s',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab content ───────────────────────────────────────────────────── */}
      <div style={{ padding: '20px 24px', maxWidth: 960, width: '100%', margin: '0 auto' }}>

        {/* ── Tab: Khám bệnh ──────────────────────────────────────────────── */}
        {activeTab === 'exam' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Lý do khám */}
            {rec?.reason && (
              <Card title="Lý do khám">
                <p style={{ fontSize: '.9rem', color: 'var(--clr-gray-700)', lineHeight: 1.7 }}>{rec.reason}</p>
              </Card>
            )}

            {/* Dấu hiệu sinh tồn */}
            <Card title="🫀 Dấu hiệu sinh tồn">
              <VitalSignsEditor examId={exam.id} disabled={isCompleted} onSaved={reload} currentExam={exam} />
            </Card>

            {/* Triệu chứng lâm sàng */}
            <Card title="📋 Triệu chứng lâm sàng">
              <SymptomsEditor
                examId={exam.id}
                value={exam.clinical_symptoms ?? ''}
                disabled={isCompleted}
                onSaved={reload}
              />
            </Card>

            {/* Chẩn đoán */}
            <Card title="🏷 Chẩn đoán ICD-10">
              <DiagnosisPanel
                examId={exam.id}
                diagnoses={exam.diagnoses}
                disabled={isCompleted}
                onChanged={reload}
              />
            </Card>
          </div>
        )}

        {/* ── Tab: Đơn thuốc ──────────────────────────────────────────────── */}
        {activeTab === 'prescription' && (
          <PrescriptionPanel
            examId={exam.id}
            items={exam.prescription_items}
            disabled={isCompleted}
            onChanged={reload}
          />
        )}

        {/* ── Tab: Chỉ định CLS ───────────────────────────────────────────── */}
        {activeTab === 'cls' && (
          <ClsPanel
            examId={exam.id}
            items={exam.prescription_items.filter(i => i.item_type === 'cls')}
            disabled={isCompleted}
            onChanged={reload}
          />
        )}

        {/* ── Tab: Tạm ứng ────────────────────────────────────────────────── */}
        {activeTab === 'deposit' && (
          <DepositPanel examId={exam.id} disabled={isCompleted} patientName={p?.full_name} />
        )}

        {/* ── Tab: Hẹn khám ───────────────────────────────────────────────── */}
        {activeTab === 'appointment' && (
          <AppointmentPanel examId={exam.id} disabled={isCompleted} onSaved={reload} currentExam={exam} />
        )}

        {/* ── Tab: Giấy BHXH ──────────────────────────────────────────────── */}
        {activeTab === 'bhxh' && (
          <BhxhPanel
            examId={exam.id}
            disabled={isCompleted}
            onSaved={reload}
            patient={p}
            exam={exam}
          />
        )}

        {/* ── Tab: Chi phí ────────────────────────────────────────────────── */}
        {activeTab === 'cost' && (
          <CostSummaryPanel examId={exam.id} />
        )}
      </div>

      <ConfirmDialog
        open={confirmComplete}
        onClose={() => setConfirmComplete(false)}
        onConfirm={handleComplete}
        title="Kết thúc khám"
        message="Xác nhận kết thúc phiếu khám? Sau khi kết thúc bạn không thể chỉnh sửa thêm."
        confirmLabel="Kết thúc"
      />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sub-panels (tất cả self-contained, tiêu chí 1: không chứa business logic)
// ═══════════════════════════════════════════════════════════════════════════════

// ── Vital Signs ───────────────────────────────────────────────────────────────
interface VitalSigns {
  temperature: string; blood_pressure: string;
  heart_rate: string;  respiratory_rate: string;
  spo2: string;        weight: string; height: string;
}

interface VitalSignsProps {
  examId: number; disabled: boolean;
  onSaved: () => void; currentExam: ExaminationResponse;
}

function VitalSignsEditor({ examId, disabled, onSaved, currentExam }: VitalSignsProps) {
  // Parse from complications field (reuse existing column for vitals JSON)
  const parseVitals = (): VitalSigns => {
    try {
      if (currentExam.complications?.startsWith('{')) {
        return JSON.parse(currentExam.complications) as VitalSigns;
      }
    } catch { /* ignore */ }
    return { temperature: '', blood_pressure: '', heart_rate: '', respiratory_rate: '', spo2: '', weight: '', height: '' };
  };

  const [vitals, setVitals] = useState<VitalSigns>(parseVitals);
  const saveAsync = useAsync<ExaminationResponse>();

  const handleSave = async () => {
    const res = await saveAsync.run(
      examinationApi.update(examId, { complications: JSON.stringify(vitals) }),
    );
    if (res) { toast.success('Đã lưu dấu hiệu sinh tồn'); onSaved(); }
    else toast.error(saveAsync.error ?? 'Lưu thất bại');
  };

  const set = (key: keyof VitalSigns) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setVitals(v => ({ ...v, [key]: e.target.value }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="form-row form-row-3">
        <VitalField label="Nhiệt độ (°C)"        value={vitals.temperature}      onChange={set('temperature')}      placeholder="36.5"     disabled={disabled} />
        <VitalField label="Huyết áp (mmHg)"       value={vitals.blood_pressure}   onChange={set('blood_pressure')}   placeholder="120/80"   disabled={disabled} />
        <VitalField label="Nhịp tim (lần/phút)"   value={vitals.heart_rate}       onChange={set('heart_rate')}       placeholder="80"       disabled={disabled} />
        <VitalField label="Nhịp thở (lần/phút)"  value={vitals.respiratory_rate} onChange={set('respiratory_rate')} placeholder="18"       disabled={disabled} />
        <VitalField label="SpO₂ (%)"              value={vitals.spo2}             onChange={set('spo2')}             placeholder="98"       disabled={disabled} />
        <VitalField label="Cân nặng (kg)"         value={vitals.weight}           onChange={set('weight')}           placeholder="60"       disabled={disabled} />
        <VitalField label="Chiều cao (cm)"        value={vitals.height}           onChange={set('height')}           placeholder="165"      disabled={disabled} />
        {vitals.weight && vitals.height && (
          <div>
            <div className="text-xs text-muted" style={{ marginBottom: 4 }}>BMI</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--clr-primary)' }}>
              {(Number(vitals.weight) / ((Number(vitals.height) / 100) ** 2)).toFixed(1)}
            </div>
          </div>
        )}
      </div>
      {!disabled && (
        <div>
          <Button size="sm" variant="secondary" loading={saveAsync.loading} onClick={handleSave}>
            💾 Lưu dấu hiệu sinh tồn
          </Button>
        </div>
      )}
    </div>
  );
}

function VitalField({ label, value, onChange, placeholder, disabled }: {
  label: string; value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string; disabled: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-muted" style={{ marginBottom: 4 }}>{label}</div>
      <input
        value={value} onChange={onChange} placeholder={placeholder} disabled={disabled}
        className="form-input" style={{ textAlign: 'center', fontWeight: 600 }}
      />
    </div>
  );
}

// ── Symptoms Editor ────────────────────────────────────────────────────────────
function SymptomsEditor({ examId, value, disabled, onSaved }: {
  examId: number; value: string; disabled: boolean; onSaved: () => void;
}) {
  const [text, setText] = useState(value);
  const saveAsync = useAsync<ExaminationResponse>();
  useEffect(() => { setText(value); }, [value]);

  const handleBlur = async () => {
    if (text === value || disabled) return;
    const res = await saveAsync.run(examinationApi.update(examId, { clinical_symptoms: text }));
    if (res) { toast.success('Đã lưu triệu chứng'); onSaved(); }
    else toast.error(saveAsync.error ?? 'Lưu thất bại');
  };

  return (
    <textarea
      className="form-input" rows={5} value={text} disabled={disabled}
      placeholder="Mô tả triệu chứng, dấu hiệu lâm sàng, tiền sử bệnh..."
      onChange={e => setText(e.target.value)}
      onBlur={handleBlur}
    />
  );
}

// ── Deposit Panel (Tạm ứng) ────────────────────────────────────────────────────
function DepositPanel({ patientName, disabled }: {
  examId: number; disabled: boolean; patientName?: string | null;
}) {
  const [amount,  setAmount]  = useState('');
  const [method,  setMethod]  = useState('cash');
  const [note,    setNote]    = useState('');
  const [records, setRecords] = useState<Array<{ id: number; amount: string; method: string; note: string; time: string }>>([]);

  const handleAdd = () => {
    if (!amount || Number(amount) <= 0) { toast.error('Nhập số tiền hợp lệ'); return; }
    setRecords(prev => [...prev, {
      id: Date.now(), amount, method, note,
      time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    }]);
    setAmount(''); setNote('');
    toast.success('Đã thêm tạm ứng');
  };

  const total = records.reduce((s, r) => s + Number(r.amount), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Summary bar */}
      <div style={{
        padding: '14px 20px', background: 'var(--clr-primary-light)', borderRadius: 12,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{ fontSize: '.9rem', color: 'var(--clr-primary-dark)' }}>
          Tổng tạm ứng — {patientName ?? ''}
        </span>
        <span style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--clr-primary)' }}>
          {total.toLocaleString('vi-VN')} ₫
        </span>
      </div>

      {/* Add form */}
      {!disabled && (
        <Card title="Thêm tạm ứng">
          <div className="form-row form-row-3" style={{ marginBottom: 12 }}>
            <Field label="Số tiền (VNĐ)" required>
              <input
                type="number" min={0} step={1000} className="form-input"
                value={amount} onChange={e => setAmount(e.target.value)}
                placeholder="500,000"
              />
            </Field>
            <Field label="Hình thức">
              <select className="form-input" value={method} onChange={e => setMethod(e.target.value)}>
                <option value="cash">Tiền mặt</option>
                <option value="transfer">Chuyển khoản</option>
                <option value="card">Thẻ ngân hàng</option>
                <option value="momo">MoMo / Ví điện tử</option>
              </select>
            </Field>
            <Field label="Ghi chú">
              <input className="form-input" value={note} onChange={e => setNote(e.target.value)} placeholder="Ghi chú..." />
            </Field>
          </div>
          <Button size="sm" onClick={handleAdd}>+ Thêm tạm ứng</Button>
        </Card>
      )}

      {/* List */}
      <Card title={`Lịch sử tạm ứng (${records.length})`}>
        {records.length === 0 ? (
          <p className="text-sm text-muted" style={{ textAlign: 'center', padding: '24px 0' }}>
            Chưa có khoản tạm ứng nào
          </p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th><th>Số tiền</th><th>Hình thức</th><th>Ghi chú</th><th>Thời gian</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r, i) => (
                  <tr key={r.id}>
                    <td className="text-sm">{i + 1}</td>
                    <td style={{ fontWeight: 700, color: 'var(--clr-primary)' }}>
                      {Number(r.amount).toLocaleString('vi-VN')} ₫
                    </td>
                    <td className="text-sm">{r.method}</td>
                    <td className="text-sm text-muted">{r.note || '—'}</td>
                    <td className="text-xs text-muted">{r.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ── Appointment Panel (Hẹn khám) ─────────────────────────────────────────────
function AppointmentPanel({ examId, disabled, onSaved, currentExam }: {
  examId: number; disabled: boolean; onSaved: () => void; currentExam: ExaminationResponse;
}) {
  const [date,    setDate]    = useState(currentExam.revisit_days
    ? new Date(Date.now() + currentExam.revisit_days * 86400000).toISOString().slice(0, 10) : '');
  const [days,    setDays]    = useState(String(currentExam.revisit_days ?? ''));
  const [reason,  setReason]  = useState('');
  const [doctor,  setDoctor]  = useState(currentExam.doctor_name ?? '');
  const saveAsync = useAsync<ExaminationResponse>();

  const handleSave = async () => {
    const res = await saveAsync.run(examinationApi.update(examId, {
      revisit_days:   days ? Number(days) : undefined,
      revisit_result: reason || undefined,
      doctor_name:    doctor || undefined,
    }));
    if (res) { toast.success('Đã lưu lịch hẹn'); onSaved(); }
    else toast.error(saveAsync.error ?? 'Lưu thất bại');
  };

  // Auto-calc days from date
  const handleDateChange = (d: string) => {
    setDate(d);
    if (d) {
      const diff = Math.round((new Date(d).getTime() - Date.now()) / 86400000);
      if (diff > 0) setDays(String(diff));
    }
  };

  const handleDaysChange = (d: string) => {
    setDays(d);
    if (d && Number(d) > 0) {
      const target = new Date(Date.now() + Number(d) * 86400000);
      setDate(target.toISOString().slice(0, 10));
    }
  };

  return (
    <Card title="📅 Phiếu hẹn tái khám">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Appointment preview */}
        {date && (
          <div style={{
            padding: '16px 20px', background: '#f0fdf4', border: '1px solid #86efac',
            borderRadius: 12, display: 'flex', alignItems: 'center', gap: 16,
          }}>
            <span style={{ fontSize: '2rem' }}>📅</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '1.05rem', color: '#166534' }}>
                Hẹn ngày: {new Date(date).toLocaleDateString('vi-VN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </div>
              {days && <div style={{ fontSize: '.85rem', color: '#16a34a' }}>Sau {days} ngày kể từ hôm nay</div>}
            </div>
          </div>
        )}

        <div className="form-row form-row-2">
          <Field label="Ngày hẹn tái khám">
            <input type="date" className="form-input" value={date} disabled={disabled}
              min={new Date().toISOString().slice(0, 10)}
              onChange={e => handleDateChange(e.target.value)} />
          </Field>
          <Field label="Số ngày (tự động tính)">
            <input type="number" className="form-input" value={days} disabled={disabled}
              min={1} placeholder="VD: 30" onChange={e => handleDaysChange(e.target.value)} />
          </Field>
        </div>

        <Field label="Bác sĩ phụ trách">
          <input className="form-input" value={doctor} disabled={disabled}
            placeholder="Bác sĩ khám lần sau..." onChange={e => setDoctor(e.target.value)} />
        </Field>

        <Field label="Lý do hẹn / dặn dò bệnh nhân">
          <textarea className="form-input" rows={3} value={reason} disabled={disabled}
            placeholder="Tái khám kiểm tra, uống thuốc đúng giờ, hạn chế ăn mặn..."
            onChange={e => setReason(e.target.value)} />
        </Field>

        {!disabled && (
          <Button size="sm" variant="secondary" loading={saveAsync.loading} onClick={handleSave}>
            💾 Lưu lịch hẹn
          </Button>
        )}
      </div>
    </Card>
  );
}

// ── BHXH Panel (Giấy nghỉ hưởng BHXH) ────────────────────────────────────────
interface BhxhProps {
  examId: number; disabled: boolean; onSaved: () => void;
  patient?: { full_name: string; birth_year?: number | null; gender?: string | null } | null;
  exam: ExaminationResponse;
}

function BhxhPanel({ disabled, patient, exam }: BhxhProps) {
  const [form, setForm] = useState({
    days:       '3',
    from_date:  new Date().toISOString().slice(0, 10),
    to_date:    '',
    diagnosis:  '',
    workplace:  '',
    note:       '',
  });

  // Auto calc to_date
  const calcToDate = (fromDate: string, daysStr: string) => {
    if (!fromDate || !daysStr) return '';
    const d = new Date(fromDate);
    d.setDate(d.getDate() + Number(daysStr) - 1);
    return d.toISOString().slice(0, 10);
  };

  const set = (key: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const updated = { ...form, [key]: e.target.value };
    if (key === 'days' || key === 'from_date') {
      updated.to_date = calcToDate(
        key === 'from_date' ? e.target.value : form.from_date,
        key === 'days'      ? e.target.value : form.days,
      );
    }
    setForm(updated);
  };

  // Init to_date
  useEffect(() => {
    setForm(f => ({ ...f, to_date: calcToDate(f.from_date, f.days) }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePrint = () => {
    window.print();
    toast.success('Đang in giấy BHXH...');
  };

  const primaryDiagnosis = exam.diagnoses.find(d => d.is_primary) ?? exam.diagnoses[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card title="📄 Thông tin giấy nghỉ hưởng BHXH">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Patient info readonly */}
          <div style={{ padding: '12px 16px', background: 'var(--clr-gray-50)', borderRadius: 8 }}>
            <div className="form-row form-row-3">
              <div><span className="text-xs text-muted">Họ tên:</span> <strong>{patient?.full_name ?? '—'}</strong></div>
              <div><span className="text-xs text-muted">Năm sinh:</span> <strong>{patient?.birth_year ?? '—'}</strong></div>
              <div><span className="text-xs text-muted">Giới tính:</span> <strong>{patient?.gender === 'male' ? 'Nam' : 'Nữ'}</strong></div>
            </div>
          </div>

          <div className="form-row form-row-3">
            <Field label="Số ngày nghỉ">
              <select className="form-input" value={form.days} disabled={disabled} onChange={set('days')}>
                {[1,2,3,4,5,7,10,14,21,28,30].map(d => (
                  <option key={d} value={d}>{d} ngày</option>
                ))}
              </select>
            </Field>
            <Field label="Từ ngày">
              <input type="date" className="form-input" value={form.from_date} disabled={disabled} onChange={set('from_date')} />
            </Field>
            <Field label="Đến ngày (tự tính)">
              <input type="date" className="form-input" value={form.to_date} readOnly
                style={{ background: 'var(--clr-gray-100)', fontWeight: 600 }} />
            </Field>
          </div>

          <Field label="Chẩn đoán (điền vào giấy BHXH)">
            <input
              className="form-input" value={form.diagnosis} disabled={disabled}
              placeholder={primaryDiagnosis?.icd_name ?? 'Chẩn đoán...'}
              defaultValue={primaryDiagnosis?.icd_name ?? ''}
              onChange={set('diagnosis')}
            />
          </Field>

          <Field label="Nơi làm việc của bệnh nhân">
            <input className="form-input" value={form.workplace} disabled={disabled}
              placeholder="Tên công ty / cơ quan..." onChange={set('workplace')} />
          </Field>

          <Field label="Ghi chú thêm">
            <textarea className="form-input" rows={2} value={form.note} disabled={disabled}
              placeholder="Dặn dò, hướng dẫn thêm..." onChange={set('note')} />
          </Field>
        </div>
      </Card>

      {/* Preview */}
      <Card title="Xem trước giấy BHXH">
        <div style={{
          padding: '28px 32px', border: '2px solid var(--clr-gray-200)', borderRadius: 8,
          fontFamily: 'serif', fontSize: '.9rem', lineHeight: 2,
          background: '#fff',
        }} id="bhxh-print">
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', textTransform: 'uppercase' }}>
              CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
            </div>
            <div style={{ fontSize: '.85rem' }}>Độc lập – Tự do – Hạnh phúc</div>
            <div style={{ marginTop: 16, fontWeight: 700, fontSize: '1.15rem', textTransform: 'uppercase' }}>
              GIẤY CHỨNG NHẬN NGHỈ VIỆC HƯỞNG BHXH
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.85rem' }}>
            <tbody>
              <BhxhRow label="Họ và tên"   value={patient?.full_name} />
              <BhxhRow label="Năm sinh"    value={patient?.birth_year} />
              <BhxhRow label="Nơi làm việc" value={form.workplace || '...........'} />
              <BhxhRow label="Chẩn đoán"   value={form.diagnosis || primaryDiagnosis?.icd_name || '...........'} />
              <BhxhRow label="Cho nghỉ"    value={`${form.days} ngày`} />
              <BhxhRow label="Từ ngày"     value={form.from_date ? new Date(form.from_date).toLocaleDateString('vi-VN') : ''} />
              <BhxhRow label="Đến ngày"    value={form.to_date ? new Date(form.to_date).toLocaleDateString('vi-VN') : ''} />
              {form.note && <BhxhRow label="Ghi chú" value={form.note} />}
            </tbody>
          </table>

          <div style={{ marginTop: 32, display: 'flex', justifyContent: 'space-between', fontSize: '.85rem' }}>
            <div style={{ textAlign: 'center', width: '45%' }}>
              <div style={{ fontWeight: 600 }}>Bệnh nhân / Người nhận</div>
              <div style={{ marginTop: 48, borderTop: '1px solid #333' }}>(Ký, ghi rõ họ tên)</div>
            </div>
            <div style={{ textAlign: 'center', width: '45%' }}>
              <div>{form.from_date ? `Ngày ${new Date(form.from_date).toLocaleDateString('vi-VN', { day: 'numeric' })} tháng ${new Date(form.from_date).toLocaleDateString('vi-VN', { month: 'numeric' })} năm ${new Date(form.from_date).getFullYear()}` : '....../....../......'}</div>
              <div style={{ fontWeight: 600 }}>Y, Bác sĩ ký tên</div>
              <div style={{ marginTop: 48, borderTop: '1px solid #333' }}>{exam.doctor_name ?? '(Ký, đóng dấu)'}</div>
            </div>
          </div>
        </div>

        {!disabled && (
          <div className="flex gap-2" style={{ marginTop: 16 }}>
            <Button size="sm" variant="secondary" onClick={handlePrint}>🖨️ In giấy</Button>
          </div>
        )}
      </Card>
    </div>
  );
}

function BhxhRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <tr>
      <td style={{ width: '30%', paddingRight: 8, fontWeight: 600, verticalAlign: 'top', paddingBottom: 6 }}>{label}:</td>
      <td style={{ paddingBottom: 6 }}>{value ?? '—'}</td>
    </tr>
  );
}

// ── Cost Summary Panel ────────────────────────────────────────────────────────
function CostSummaryPanel({ examId }: { examId: number }) {
  const { data, loading, run } = useAsync<Record<string, number>>();
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => { run(examinationApi.cost(examId)); }, [examId, refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const fmt = (v?: number) => v !== undefined ? v.toLocaleString('vi-VN') + ' ₫' : '—';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card title="🧾 Tổng hợp chi phí"
        actions={<Button size="sm" variant="ghost" onClick={() => setRefreshKey(k => k + 1)}>↻ Cập nhật</Button>}
      >
        {loading ? (
          <LoadingOverlay />
        ) : !data ? (
          <p className="text-sm text-muted" style={{ textAlign: 'center', padding: 24 }}>Chưa có dữ liệu chi phí</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {[
              { label: '💊 Tiền thuốc',        key: 'drug_total',     color: 'var(--clr-primary)'  },
              { label: '🔬 Tiền CLS',           key: 'cls_total',      color: 'var(--clr-primary)'  },
              { label: '📋 Tổng cộng',          key: 'total',          color: 'var(--clr-gray-800)', bold: true },
              { label: '🏥 BHYT chi trả',       key: 'bhyt_total',     color: '#059669' },
              { label: '👤 Bệnh nhân chi trả',  key: 'patient_total',  color: 'var(--clr-danger)',  bold: true },
            ].map(item => (
              <div key={item.key} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '12px 0', borderBottom: '1px solid var(--clr-gray-100)',
              }}>
                <span style={{ fontSize: '.9rem', color: 'var(--clr-gray-600)' }}>{item.label}</span>
                <span style={{ fontSize: item.bold ? '1.1rem' : '1rem', fontWeight: item.bold ? 800 : 600, color: item.color }}>
                  {fmt(data[item.key])}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

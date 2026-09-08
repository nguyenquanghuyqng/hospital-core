/**
 * ExaminationPage — phiếu khám bệnh.
 * Tiêu chí 1: Component không chứa business logic — gọi API, hiển thị state.
 * Tiêu chí 9: loading / error / empty state thống nhất.
 */
import { useEffect, useCallback, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { examinationApi } from '@api/examination.api';
import { receptionApi } from '@api/reception.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatusBadge, LoadingOverlay, ErrorState, ConfirmDialog } from '@components/ui';
import { fmtDate, fmtDateTime } from '@lib/utils';
import { ROUTES } from '@/app/routes';
import type { ExaminationResponse, ReceptionResponse } from '@/types';
import DiagnosisPanel from '../components/DiagnosisPanel';
import PrescriptionPanel from '../components/PrescriptionPanel';

export default function ExaminationPage() {
  const { receptionId } = useParams<{ receptionId: string }>();
  const navigate = useNavigate();

  const receptionAsync   = useAsync<ReceptionResponse>();
  const examinationAsync = useAsync<ExaminationResponse>();
  const actionAsync      = useAsync<ExaminationResponse>();
  const [confirmComplete, setConfirmComplete] = useState(false);

  // ── Load / create examination ──────────────────────────────────────────────
  const loadOrCreate = useCallback(async () => {
    if (!receptionId) return;
    const rid = Number(receptionId);
    await receptionAsync.run(receptionApi.get(rid));

    let exam = await examinationAsync.run(
      examinationApi.getByReception(rid).catch(() => null as unknown as ExaminationResponse),
    );
    if (!exam) {
      exam = await examinationAsync.run(
        examinationApi.create({ reception_id: rid }),
      );
    }
  }, [receptionId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { void loadOrCreate(); }, [loadOrCreate]);

  const reload = () => {
    if (receptionId) {
      examinationAsync.run(examinationApi.getByReception(Number(receptionId)));
    }
  };

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
    if (res) {
      toast.success('Đã kết thúc khám!');
      navigate(ROUTES.DOCTOR);
    } else toast.error(actionAsync.error ?? 'Thất bại');
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  if (receptionAsync.loading || examinationAsync.loading) return <LoadingOverlay />;
  if (examinationAsync.error) return (
    <ErrorState message={examinationAsync.error} onRetry={loadOrCreate} />
  );

  const exam = examinationAsync.data;
  const rec  = receptionAsync.data;
  if (!exam) return null;

  const isCompleted = exam.status === 'completed';
  const p = rec?.patient;

  return (
    <div className="page-container" style={{ maxWidth: 900 }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-4" style={{ flexWrap: 'wrap' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>← Quay lại</Button>
        <h1 style={{ fontSize: '1.2rem', fontWeight: 700, flex: 1 }}>
          Phiếu khám — {p?.full_name ?? `BN #${exam.patient_id}`}
        </h1>
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

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Patient summary */}
        <Card title="Thông tin bệnh nhân & lượt khám">
          <div className="grid-3">
            <Row label="Bệnh nhân"  value={p?.full_name} />
            <Row label="Năm sinh"   value={p?.birth_year} />
            <Row label="Giới tính"  value={p?.gender === 'male' ? 'Nam' : p?.gender === 'female' ? 'Nữ' : '—'} />
            <Row label="Phòng khám" value={rec?.clinic_room} />
            <Row label="Ngày khám"  value={fmtDate(exam.exam_date)} />
            <Row label="Bắt đầu"    value={fmtDateTime(exam.exam_start_at)} />
            <Row label="Bác sĩ"     value={exam.doctor_name} />
            <Row label="Đối tượng"  value={rec?.subject_name} />
            <Row label="BHYT"       value={exam.insurance_number} />
          </div>
          {rec?.reason && (
            <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--clr-gray-50)', borderRadius: 8, fontSize: '.875rem' }}>
              <strong>Lý do khám:</strong> {rec.reason}
            </div>
          )}
        </Card>

        {/* Clinical symptoms */}
        <Card title="Triệu chứng lâm sàng">
          <SymptomsEditor
            examId={exam.id}
            value={exam.clinical_symptoms ?? ''}
            disabled={isCompleted}
            onSaved={reload}
          />
        </Card>

        {/* Diagnoses */}
        <Card title="Chẩn đoán ICD-10">
          <DiagnosisPanel
            examId={exam.id}
            diagnoses={exam.diagnoses}
            disabled={isCompleted}
            onChanged={reload}
          />
        </Card>

        {/* Prescription */}
        <Card title="Kê đơn thuốc & chỉ định CLS">
          <PrescriptionPanel
            examId={exam.id}
            items={exam.prescription_items}
            disabled={isCompleted}
            onChanged={reload}
          />
        </Card>

        {/* Cost summary */}
        <CostSummary examId={exam.id} />
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <div className="text-xs text-muted" style={{ marginBottom: 2 }}>{label}</div>
      <div className="text-sm font-medium" style={{ color: 'var(--clr-gray-800)' }}>{value ?? '—'}</div>
    </div>
  );
}

function SymptomsEditor({
  examId, value, disabled, onSaved,
}: { examId: number; value: string; disabled: boolean; onSaved: () => void }) {
  const [text, setText] = useState(value);
  const saveAsync = useAsync<ExaminationResponse>();

  useEffect(() => { setText(value); }, [value]);

  const handleBlur = async () => {
    if (text === value || disabled) return;
    const res = await saveAsync.run(
      examinationApi.update(examId, { clinical_symptoms: text }),
    );
    if (res) { toast.success('Đã lưu triệu chứng'); onSaved(); }
    else toast.error(saveAsync.error ?? 'Lưu thất bại');
  };

  return (
    <textarea
      className="form-input"
      rows={4}
      value={text}
      disabled={disabled}
      placeholder="Mô tả triệu chứng, dấu hiệu lâm sàng..."
      onChange={e => setText(e.target.value)}
      onBlur={handleBlur}
    />
  );
}

function CostSummary({ examId }: { examId: number }) {
  const { data, loading, run } = useAsync<Record<string, number>>();

  useEffect(() => { run(examinationApi.cost(examId)); }, [examId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return null;
  if (!data)   return null;

  const fmt = (v?: number) => v !== undefined ? v.toLocaleString('vi-VN') + ' ₫' : '—';

  return (
    <Card title="Tổng hợp chi phí">
      <div className="grid-3">
        <Row label="Tiền thuốc"    value={fmt(data['drug_total'])} />
        <Row label="Tiền CLS"      value={fmt(data['cls_total'])} />
        <Row label="Tổng cộng"     value={fmt(data['total'])} />
        <Row label="BHYT chi trả"  value={fmt(data['bhyt_total'])} />
        <Row label="BN chi trả"    value={fmt(data['patient_total'])} />
      </div>
    </Card>
  );
}

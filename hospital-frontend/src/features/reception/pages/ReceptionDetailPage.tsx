import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { receptionApi } from '@api/reception.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatusBadge, LoadingOverlay, ErrorState } from '@components/ui';
import { fmtDate, fmtDateTime, fmtGender } from '@lib/utils';
import { ROUTES, toPath } from '@/app/routes';
import type { ReceptionResponse } from '@/types';

export default function ReceptionDetailPage() {
  const { id }   = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: reception, loading, error, run } = useAsync<ReceptionResponse>();
  const completeAsync = useAsync<unknown>();

  useEffect(() => {
    if (id) run(receptionApi.get(Number(id)));
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleComplete = async () => {
    if (!id) return;
    const res = await completeAsync.run(receptionApi.complete(Number(id)));
    if (res !== null) { toast.success('Đã hoàn tất lượt khám'); run(receptionApi.get(Number(id))); }
    else toast.error(completeAsync.error ?? 'Thất bại');
  };

  if (loading) return <LoadingOverlay />;
  if (error)   return <ErrorState message={error} onRetry={() => id && run(receptionApi.get(Number(id)))} />;
  if (!reception) return null;

  const p = reception.patient;

  return (
    <div className="page-container" style={{ maxWidth: 760 }}>
      <div className="flex items-center gap-3 mb-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.RECEPTION)}>← Quay lại</Button>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
          Chi tiết lượt khám #{reception.visit_number ?? reception.id}
        </h1>
        <StatusBadge status={reception.status} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Patient */}
        <Card title="Thông tin bệnh nhân">
          <div className="grid-2">
            <Row label="Họ và tên"  value={p?.full_name} />
            <Row label="Năm sinh"   value={p?.birth_year ?? fmtDate(p?.date_of_birth)} />
            <Row label="Giới tính"  value={fmtGender(p?.gender)} />
            <Row label="CCCD/CMND"  value={p?.cccd} />
            <Row label="Số điện thoại" value={p?.phone} />
            <Row label="Mã BN"      value={p?.patient_code} />
          </div>
        </Card>

        {/* Visit */}
        <Card title="Thông tin lượt khám">
          <div className="grid-2">
            <Row label="Ngày khám"     value={fmtDate(reception.visit_date)} />
            <Row label="Giờ đăng ký"   value={reception.visit_time} />
            <Row label="Phòng khám"    value={reception.clinic_room} />
            <Row label="Số khám"       value={reception.visit_number} />
            <Row label="Đối tượng"     value={reception.subject_name} />
            <Row label="Số thẻ BHYT"   value={reception.insurance_number} />
            <Row label="Thời gian check-in" value={fmtDateTime(reception.checked_in_at)} />
            <Row label="Hoàn thành lúc"    value={fmtDateTime(reception.completed_at)} />
          </div>
          {reception.reason && (
            <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--clr-gray-50)', borderRadius: 8 }}>
              <strong>Lý do khám:</strong> {reception.reason}
            </div>
          )}
        </Card>

        {/* Actions */}
        {(reception.status === 'checked_in') && (
          <div className="flex gap-3" style={{ justifyContent: 'flex-end' }}>
            <Button
              onClick={() => navigate(toPath(ROUTES.EXAMINATION, { receptionId: reception.id }))}
            >
              🩺 Mở phiếu khám
            </Button>
            <Button variant="secondary" loading={completeAsync.loading} onClick={handleComplete}>
              Hoàn tất không cần phiếu
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div>
      <div className="text-xs text-muted" style={{ marginBottom: 2 }}>{label}</div>
      <div className="text-sm font-medium" style={{ color: 'var(--clr-gray-800)' }}>{value ?? '—'}</div>
    </div>
  );
}

import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { receptionApi } from '@api/reception.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, LoadingOverlay, ErrorState, StatusBadge } from '@components/ui';
import { fmtDate, fmtGender } from '@lib/utils';
import { ROUTES, toPath } from '@/app/routes';
import type { ReceptionResponse } from '@/types';

export default function DoctorPatientPage() {
  const { receptionId } = useParams<{ receptionId: string }>();
  const navigate = useNavigate();
  const { data: reception, loading, error, run } = useAsync<ReceptionResponse>();

  useEffect(() => {
    if (receptionId) run(receptionApi.get(Number(receptionId)));
  }, [receptionId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <LoadingOverlay />;
  if (error)   return <ErrorState message={error} />;
  if (!reception) return null;

  const p = reception.patient;

  return (
    <div className="page-container" style={{ maxWidth: 760 }}>
      <div className="flex items-center gap-3 mb-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(ROUTES.DOCTOR)}>← Hàng đợi</Button>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Hồ sơ bệnh nhân</h1>
        <StatusBadge status={reception.visit_status} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <Card title="Thông tin bệnh nhân">
          <div className="grid-2">
            <Row label="Họ và tên"  value={p?.full_name} />
            <Row label="Năm sinh"   value={p?.birth_year ?? fmtDate(p?.date_of_birth)} />
            <Row label="Giới tính"  value={fmtGender(p?.gender)} />
            <Row label="Số điện thoại" value={p?.phone} />
            <Row label="Mã BN"      value={p?.patient_code} />
            <Row label="Phòng khám" value={reception.clinic_room} />
          </div>
          {reception.reason && (
            <div style={{ marginTop: 16, padding: '12px 16px', background: 'var(--clr-gray-50)', borderRadius: 8 }}>
              <strong>Lý do khám:</strong> {reception.reason}
            </div>
          )}
        </Card>

        <div className="flex gap-3" style={{ justifyContent: 'flex-end' }}>
          <Button onClick={() => navigate(toPath(ROUTES.EXAMINATION, { receptionId: reception.id }))}>
            📝 Mở phiếu khám
          </Button>
        </div>
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

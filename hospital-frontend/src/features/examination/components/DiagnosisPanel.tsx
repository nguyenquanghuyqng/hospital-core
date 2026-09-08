import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { examinationApi } from '@api/examination.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Field, EmptyState } from '@components/ui';
import type { DiagnosisResponse } from '@/types';

const schema = z.object({
  icd_code:   z.string().optional(),
  icd_name:   z.string().min(2, 'Tên chẩn đoán tối thiểu 2 ký tự'),
  is_primary: z.boolean().default(false),
  note:       z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  examId:    number;
  diagnoses: DiagnosisResponse[];
  disabled:  boolean;
  onChanged: () => void;
}

export default function DiagnosisPanel({ examId, diagnoses, disabled, onChanged }: Props) {
  const [adding, setAdding] = useState(false);
  const addAsync = useAsync<DiagnosisResponse>();
  const delAsync = useAsync<void>();

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { is_primary: false },
  });

  const onAdd = async (data: FormValues) => {
    const res = await addAsync.run(
      examinationApi.addDiagnosis(examId, {
        icd_code: data.icd_code || undefined,
        icd_name: data.icd_name,
        is_primary: data.is_primary,
        note: data.note || undefined,
      }),
    );
    if (res) { toast.success('Đã thêm chẩn đoán'); reset(); setAdding(false); onChanged(); }
    else toast.error(addAsync.error ?? 'Thêm thất bại');
  };

  const onDelete = async (diagId: number) => {
    await delAsync.run(examinationApi.deleteDiagnosis(examId, diagId));
    toast.success('Đã xoá chẩn đoán');
    onChanged();
  };

  return (
    <div>
      {diagnoses.length === 0 && !adding && (
        <EmptyState icon="📋" title="Chưa có chẩn đoán" description="Thêm chẩn đoán ICD-10 bên dưới." />
      )}

      {/* List */}
      {diagnoses.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
          {diagnoses.map(d => (
            <div key={d.id} style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
              background: d.is_primary ? 'var(--clr-primary-light)' : 'var(--clr-gray-50)',
              borderRadius: 8, border: `1px solid ${d.is_primary ? 'var(--clr-primary)' : 'var(--clr-gray-100)'}`,
            }}>
              {d.is_primary && <span style={{ fontSize: '.7rem', background: 'var(--clr-primary)', color: '#fff', padding: '1px 8px', borderRadius: 9999, flexShrink: 0 }}>Chính</span>}
              <span style={{ fontWeight: 600, fontSize: '.85rem', color: 'var(--clr-primary-dark)', flexShrink: 0 }}>{d.icd_code ?? '—'}</span>
              <span style={{ flex: 1, fontSize: '.875rem' }}>{d.icd_name}</span>
              {d.note && <span className="text-xs text-muted">{d.note}</span>}
              {!disabled && (
                <button
                  onClick={() => onDelete(d.id)}
                  style={{ background: 'none', border: 'none', color: 'var(--clr-danger)', cursor: 'pointer', fontSize: '1rem', padding: '2px 6px' }}
                  aria-label="Xoá chẩn đoán"
                >✕</button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      {!disabled && (
        adding ? (
          <form onSubmit={handleSubmit(onAdd)} style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: 16, background: 'var(--clr-gray-50)', borderRadius: 10 }}>
            <div className="form-row form-row-2">
              <Field label="Mã ICD-10">
                <input {...register('icd_code')} className="form-input" placeholder="VD: J18.9" />
              </Field>
              <Field label="Tên chẩn đoán" required error={errors.icd_name?.message}>
                <input {...register('icd_name')} className={`form-input${errors.icd_name ? ' error' : ''}`} placeholder="Tên bệnh / chẩn đoán" autoFocus />
              </Field>
            </div>
            <div className="form-row form-row-2">
              <Field label="Ghi chú">
                <input {...register('note')} className="form-input" placeholder="Ghi chú thêm" />
              </Field>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingTop: 22 }}>
                <input {...register('is_primary')} type="checkbox" id="is_primary" />
                <label htmlFor="is_primary" className="text-sm">Chẩn đoán chính</label>
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={addAsync.loading}>Thêm</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => { setAdding(false); reset(); }}>Huỷ</Button>
            </div>
          </form>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>+ Thêm chẩn đoán</Button>
        )
      )}
    </div>
  );
}

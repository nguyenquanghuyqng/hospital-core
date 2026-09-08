/**
 * PrescriptionPanel — Đơn thuốc.
 * Hiển thị 2 nhóm tách biệt: Thuốc BHYT và Thuốc ngoài BHYT.
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { examinationApi } from '@api/examination.api';
import { useAsync } from '@hooks/useAsync';
import { Button, Field, EmptyState, Badge } from '@components/ui';
import type { PrescriptionItemResponse } from '@/types';

const schema = z.object({
  item_code:         z.string().optional(),
  item_name:         z.string().min(1, 'Tên thuốc là bắt buộc'),
  unit:              z.string().optional(),
  quantity:          z.coerce.number().positive().default(1),
  unit_price:        z.coerce.number().min(0).optional().or(z.literal('')),
  usage_instruction: z.string().optional(),
  payment_type:      z.string().default('bhyt'),
  morning:           z.string().optional(),
  noon:              z.string().optional(),
  afternoon:         z.string().optional(),
  evening:           z.string().optional(),
  how_to_use:        z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

// Common drug units
const UNITS = ['viên', 'nang', 'gói', 'ống', 'chai', 'lọ', 'tuýp', 'hộp'];

interface Props {
  examId:    number;
  items:     PrescriptionItemResponse[];
  disabled:  boolean;
  onChanged: () => void;
}

export default function PrescriptionPanel({ examId, items, disabled, onChanged }: Props) {
  const [adding,      setAdding]      = useState(false);
  const [activeGroup, setActiveGroup] = useState<'bhyt' | 'ngoai_bhyt'>('bhyt');
  const addAsync = useAsync<PrescriptionItemResponse>();
  const delAsync = useAsync<void>();

  const { register, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { quantity: 1, payment_type: 'bhyt' },
  });

  // ── Group items ─────────────────────────────────────────────────────────────
  const drugsOnly    = items.filter(i => i.item_type === 'drug');
  const bhytDrugs    = drugsOnly.filter(i => i.payment_type === 'bhyt');
  const nonBhytDrugs = drugsOnly.filter(i => i.payment_type !== 'bhyt');

  // Auto-build usage_instruction from morning/noon/afternoon/evening
  const morning   = watch('morning');
  const noon      = watch('noon');
  const afternoon = watch('afternoon');
  const evening   = watch('evening');
  const howToUse  = watch('how_to_use');

  const buildInstruction = () => {
    const parts = [];
    if (morning)   parts.push(`Sáng ${morning}`);
    if (noon)      parts.push(`Trưa ${noon}`);
    if (afternoon) parts.push(`Chiều ${afternoon}`);
    if (evening)   parts.push(`Tối ${evening}`);
    const times = parts.join(', ');
    return [times, howToUse].filter(Boolean).join(' — ');
  };

  const onAdd = async (data: FormValues) => {
    const instruction = buildInstruction() || data.usage_instruction || undefined;
    const res = await addAsync.run(
      examinationApi.addItem(examId, {
        item_type:         'drug',
        item_name:         data.item_name,
        item_code:         data.item_code || undefined,
        unit:              data.unit || undefined,
        quantity:          data.quantity,
        unit_price:        data.unit_price ? Number(data.unit_price) : undefined,
        usage_instruction: instruction,
        payment_type:      data.payment_type,
      }),
    );
    if (res) {
      toast.success('Đã thêm thuốc');
      reset(); setAdding(false); onChanged();
    } else toast.error(addAsync.error ?? 'Thêm thất bại');
  };

  const onDelete = async (id: number) => {
    await delAsync.run(examinationApi.deleteItem(examId, id));
    toast.success('Đã xoá');
    onChanged();
  };

  const fmtMoney = (v?: number | null) =>
    v != null ? v.toLocaleString('vi-VN') + ' ₫' : '';

  // Total per group
  const bhytTotal    = bhytDrugs.reduce((s, i)    => s + (Number(i.total_amount) || 0), 0);
  const nonBhytTotal = nonBhytDrugs.reduce((s, i) => s + (Number(i.total_amount) || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Group toggle */}
      <div style={{ display: 'flex', gap: 0, background: 'var(--clr-gray-100)', borderRadius: 10, padding: 4 }}>
        {([
          { key: 'bhyt',       label: `💊 Thuốc BHYT (${bhytDrugs.length})`,         total: bhytTotal    },
          { key: 'ngoai_bhyt', label: `💊 Thuốc ngoài BHYT (${nonBhytDrugs.length})`, total: nonBhytTotal },
        ] as const).map(g => (
          <button key={g.key} onClick={() => { setActiveGroup(g.key); setAdding(false); }}
            style={{
              flex: 1, padding: '8px 16px', border: 'none', borderRadius: 8, cursor: 'pointer',
              fontFamily: 'var(--font-sans)', fontSize: '.875rem', fontWeight: 600,
              background: activeGroup === g.key ? '#fff' : 'transparent',
              color: activeGroup === g.key ? 'var(--clr-primary)' : 'var(--clr-gray-500)',
              boxShadow: activeGroup === g.key ? 'var(--shadow-sm)' : 'none',
              transition: 'all .15s',
            }}>
            {g.label}
            {g.total > 0 && (
              <span style={{ marginLeft: 8, fontSize: '.78rem', color: activeGroup === g.key ? 'var(--clr-primary)' : 'var(--clr-gray-400)' }}>
                ({g.total.toLocaleString('vi-VN')} ₫)
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Drug list */}
      {(activeGroup === 'bhyt' ? bhytDrugs : nonBhytDrugs).length === 0 && !adding ? (
        <EmptyState
          icon="💊"
          title={`Chưa có thuốc ${activeGroup === 'bhyt' ? 'BHYT' : 'ngoài BHYT'}`}
          description="Nhấn '+ Thêm thuốc' để kê đơn."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(activeGroup === 'bhyt' ? bhytDrugs : nonBhytDrugs).map((item, idx) => (
            <DrugRow
              key={item.id}
              item={item}
              idx={idx}
              disabled={disabled}
              onDelete={onDelete}
              fmtMoney={fmtMoney}
            />
          ))}
        </div>
      )}

      {/* Add form */}
      {!disabled && (
        adding ? (
          <form onSubmit={handleSubmit(onAdd)}
            style={{ padding: 16, background: 'var(--clr-gray-50)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ fontWeight: 700, fontSize: '.9rem', color: 'var(--clr-gray-700)' }}>
              Thêm thuốc {activeGroup === 'bhyt' ? 'BHYT' : 'ngoài BHYT'}
            </div>

            <div className="form-row form-row-2">
              <Field label="Mã thuốc">
                <input {...register('item_code')} className="form-input" placeholder="VD: H01BA02" />
              </Field>
              <Field label="Loại chi trả">
                <select {...register('payment_type')} className="form-input">
                  {activeGroup === 'bhyt' ? (
                    <option value="bhyt">BHYT</option>
                  ) : (
                    <>
                      <option value="fee">Dịch vụ (thu phí)</option>
                      <option value="request">Theo yêu cầu</option>
                      <option value="free">Miễn phí</option>
                      <option value="consume">Hao phí vật tư</option>
                    </>
                  )}
                </select>
              </Field>
            </div>

            <Field label="Tên thuốc" required error={errors.item_name?.message}>
              <input {...register('item_name')}
                className={`form-input${errors.item_name ? ' error' : ''}`}
                placeholder="Tên thuốc, hoạt chất..." autoFocus />
            </Field>

            <div className="form-row form-row-3">
              <Field label="Đơn vị">
                <select {...register('unit')} className="form-input">
                  <option value="">—</option>
                  {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </Field>
              <Field label="Số lượng" required>
                <input {...register('quantity')} type="number" min={0.01} step={1} className="form-input" />
              </Field>
              <Field label="Đơn giá (VNĐ)">
                <input {...register('unit_price')} type="number" min={0} className="form-input" placeholder="0" />
              </Field>
            </div>

            {/* Dosage builder */}
            <div style={{ background: '#fff', border: '1px solid var(--clr-gray-200)', borderRadius: 8, padding: '12px 16px' }}>
              <div className="text-xs text-muted" style={{ marginBottom: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.06em' }}>
                Liều dùng
              </div>
              <div className="form-row form-row-3" style={{ marginBottom: 10 }}>
                <Field label="Sáng">
                  <input {...register('morning')} className="form-input" placeholder="1 viên" />
                </Field>
                <Field label="Trưa">
                  <input {...register('noon')} className="form-input" placeholder="0" />
                </Field>
                <Field label="Chiều">
                  <input {...register('afternoon')} className="form-input" placeholder="0" />
                </Field>
                <Field label="Tối">
                  <input {...register('evening')} className="form-input" placeholder="1 viên" />
                </Field>
                <Field label="Cách dùng">
                  <input {...register('how_to_use')} className="form-input" placeholder="sau ăn, trước ngủ..." />
                </Field>
              </div>
              {(morning || noon || afternoon || evening) && (
                <div style={{ padding: '8px 12px', background: 'var(--clr-primary-light)', borderRadius: 6, fontSize: '.83rem', color: 'var(--clr-primary-dark)' }}>
                  📋 {buildInstruction()}
                </div>
              )}
            </div>

            <Field label="Hướng dẫn thêm (nếu có)">
              <input {...register('usage_instruction')} className="form-input"
                placeholder="Nhập trực tiếp nếu không dùng ô liều ở trên" />
            </Field>

            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={addAsync.loading}>Thêm thuốc</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => { setAdding(false); reset(); }}>Huỷ</Button>
            </div>
          </form>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => { setAdding(true); setValue('payment_type', activeGroup === 'bhyt' ? 'bhyt' : 'fee'); }}>
            + Thêm thuốc {activeGroup === 'bhyt' ? 'BHYT' : 'ngoài BHYT'}
          </Button>
        )
      )}
    </div>
  );
}

// ── Drug row ───────────────────────────────────────────────────────────────────
function DrugRow({ item, idx, disabled, onDelete, fmtMoney }: {
  item: PrescriptionItemResponse;
  idx: number;
  disabled: boolean;
  onDelete: (id: number) => void;
  fmtMoney: (v?: number | null) => string;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12, padding: '11px 14px',
      background: '#fff', border: '1px solid var(--clr-gray-100)', borderRadius: 8,
    }}>
      <span style={{
        minWidth: 26, height: 26, borderRadius: '50%', background: 'var(--clr-primary-light)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '.78rem', fontWeight: 700, color: 'var(--clr-primary-dark)', flexShrink: 0, marginTop: 1,
      }}>{idx + 1}</span>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: '.875rem', color: 'var(--clr-gray-800)' }}>
          {item.item_name}
          {item.item_code && <span style={{ marginLeft: 8, fontSize: '.75rem', color: 'var(--clr-gray-400)' }}>({item.item_code})</span>}
        </div>
        <div className="flex gap-3 mt-1" style={{ flexWrap: 'wrap' }}>
          <span className="text-xs text-muted">SL: <strong>{item.quantity}</strong> {item.unit ?? ''}</span>
          {item.usage_instruction && (
            <span style={{ fontSize: '.78rem', color: 'var(--clr-primary-dark)', background: 'var(--clr-primary-light)', padding: '1px 8px', borderRadius: 4 }}>
              {item.usage_instruction}
            </span>
          )}
          <Badge variant={item.payment_type}>{item.payment_type.toUpperCase()}</Badge>
        </div>
      </div>

      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        {item.total_amount != null && (
          <div style={{ fontWeight: 700, fontSize: '.9rem', color: 'var(--clr-primary-dark)' }}>
            {fmtMoney(item.total_amount)}
          </div>
        )}
        {item.unit_price != null && (
          <div className="text-xs text-muted">{fmtMoney(item.unit_price)}/đv</div>
        )}
      </div>

      {!disabled && (
        <button
          onClick={() => onDelete(item.id)}
          style={{ background: 'none', border: 'none', color: 'var(--clr-danger)', cursor: 'pointer', padding: '2px 4px', fontSize: '1rem', marginTop: 1 }}
          aria-label="Xoá"
        >✕</button>
      )}
    </div>
  );
}

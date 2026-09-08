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
  item_type:         z.enum(['drug', 'cls']),
  item_code:         z.string().optional(),
  item_name:         z.string().min(1, 'Tên thuốc / dịch vụ là bắt buộc'),
  unit:              z.string().optional(),
  quantity:          z.coerce.number().positive().default(1),
  unit_price:        z.coerce.number().min(0).optional().or(z.literal('')),
  usage_instruction: z.string().optional(),
  payment_type:      z.string().default('bhyt'),
});
type FormValues = z.infer<typeof schema>;

interface Props {
  examId:   number;
  items:    PrescriptionItemResponse[];
  disabled: boolean;
  onChanged: () => void;
}

export default function PrescriptionPanel({ examId, items, disabled, onChanged }: Props) {
  const [adding, setAdding] = useState(false);
  const addAsync = useAsync<PrescriptionItemResponse>();
  const delAsync = useAsync<void>();

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { item_type: 'drug', quantity: 1, payment_type: 'bhyt' },
  });
  const itemType = watch('item_type');

  const drugs = items.filter(i => i.item_type === 'drug');
  const clsItems = items.filter(i => i.item_type === 'cls');

  const onAdd = async (data: FormValues) => {
    const res = await addAsync.run(
      examinationApi.addItem(examId, {
        item_type:   data.item_type,
        item_name:   data.item_name,
        item_code:   data.item_code || undefined,
        unit:        data.unit || undefined,
        quantity:    data.quantity,
        unit_price:  data.unit_price ? Number(data.unit_price) : undefined,
        usage_instruction: data.usage_instruction || undefined,
        payment_type: data.payment_type,
      }),
    );
    if (res) { toast.success('Đã thêm'); reset(); setAdding(false); onChanged(); }
    else toast.error(addAsync.error ?? 'Thêm thất bại');
  };

  const onDelete = async (itemId: number) => {
    await delAsync.run(examinationApi.deleteItem(examId, itemId));
    toast.success('Đã xoá');
    onChanged();
  };

  const fmtMoney = (v?: number | null) => v !== undefined && v !== null ? v.toLocaleString('vi-VN') + ' ₫' : '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Drugs */}
      <div>
        <div className="text-sm font-semibold" style={{ marginBottom: 8, color: 'var(--clr-gray-700)' }}>💊 Thuốc ({drugs.length})</div>
        {drugs.length === 0 && <p className="text-xs text-muted">Chưa có đơn thuốc</p>}
        {drugs.map(item => (
          <ItemRow key={item.id} item={item} disabled={disabled} onDelete={onDelete} fmtMoney={fmtMoney} />
        ))}
      </div>

      {/* CLS */}
      <div>
        <div className="text-sm font-semibold" style={{ marginBottom: 8, color: 'var(--clr-gray-700)' }}>🔬 Chỉ định CLS ({clsItems.length})</div>
        {clsItems.length === 0 && <p className="text-xs text-muted">Chưa có chỉ định CLS</p>}
        {clsItems.map(item => (
          <ItemRow key={item.id} item={item} disabled={disabled} onDelete={onDelete} fmtMoney={fmtMoney} />
        ))}
      </div>

      {/* Add form */}
      {!disabled && (
        adding ? (
          <form onSubmit={handleSubmit(onAdd)} style={{ padding: 16, background: 'var(--clr-gray-50)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="form-row form-row-3">
              <Field label="Loại">
                <select {...register('item_type')} className="form-input">
                  <option value="drug">Thuốc</option>
                  <option value="cls">CLS</option>
                </select>
              </Field>
              <Field label="Mã thuốc / DV">
                <input {...register('item_code')} className="form-input" placeholder="Mã (tuỳ chọn)" />
              </Field>
              <Field label="Loại chi trả">
                <select {...register('payment_type')} className="form-input">
                  <option value="bhyt">BHYT</option>
                  <option value="fee">Dịch vụ</option>
                  <option value="free">Miễn phí</option>
                </select>
              </Field>
            </div>

            <Field label="Tên thuốc / dịch vụ CLS" required error={errors.item_name?.message}>
              <input {...register('item_name')} className={`form-input${errors.item_name ? ' error' : ''}`} placeholder="Nhập tên..." autoFocus />
            </Field>

            <div className="form-row form-row-3">
              <Field label="Đơn vị">
                <input {...register('unit')} className="form-input" placeholder="viên / ống / lần" />
              </Field>
              <Field label="Số lượng" required>
                <input {...register('quantity')} type="number" min={0.01} step={0.01} className="form-input" />
              </Field>
              <Field label="Đơn giá (VNĐ)">
                <input {...register('unit_price')} type="number" min={0} className="form-input" placeholder="0" />
              </Field>
            </div>

            {itemType === 'drug' && (
              <Field label="Cách dùng">
                <input {...register('usage_instruction')} className="form-input" placeholder="Sáng 1v, tối 1v sau ăn..." />
              </Field>
            )}

            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={addAsync.loading}>Thêm</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => { setAdding(false); reset(); }}>Huỷ</Button>
            </div>
          </form>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>+ Thêm thuốc / CLS</Button>
        )
      )}

      {items.length === 0 && !adding && (
        <EmptyState icon="💊" title="Chưa có đơn thuốc hoặc CLS" description="Nhấn '+ Thêm' để kê đơn." />
      )}
    </div>
  );
}

function ItemRow({
  item, disabled, onDelete, fmtMoney,
}: {
  item: PrescriptionItemResponse;
  disabled: boolean;
  onDelete: (id: number) => void;
  fmtMoney: (v?: number | null) => string;
}) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
      background: '#fff', border: '1px solid var(--clr-gray-100)', borderRadius: 8, marginBottom: 6,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="text-sm font-medium" style={{ color: 'var(--clr-gray-800)' }}>{item.item_name}</div>
        <div className="flex gap-2 mt-1">
          {item.item_code && <span className="text-xs text-muted">{item.item_code}</span>}
          <span className="text-xs text-muted">SL: {item.quantity} {item.unit ?? ''}</span>
          {item.usage_instruction && <span className="text-xs text-muted">— {item.usage_instruction}</span>}
        </div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        {item.total_amount !== null && item.total_amount !== undefined && (
          <div className="text-sm font-semibold" style={{ color: 'var(--clr-primary-dark)' }}>
            {fmtMoney(item.total_amount)}
          </div>
        )}
        <Badge variant={item.payment_type}>{item.payment_type.toUpperCase()}</Badge>
      </div>
      {!disabled && (
        <button
          onClick={() => onDelete(item.id)}
          style={{ background: 'none', border: 'none', color: 'var(--clr-danger)', cursor: 'pointer', padding: '2px 6px', fontSize: '1rem' }}
          aria-label="Xoá"
        >✕</button>
      )}
    </div>
  );
}

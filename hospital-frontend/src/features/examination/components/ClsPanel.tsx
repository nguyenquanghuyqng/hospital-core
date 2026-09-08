/**
 * ClsPanel — Chỉ định cận lâm sàng (CLS).
 * Tách khỏi PrescriptionPanel để có thêm chức năng ghi kết quả CLS.
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

const addSchema = z.object({
  item_code:    z.string().optional(),
  item_name:    z.string().min(1, 'Tên chỉ định là bắt buộc'),
  unit:         z.string().optional(),
  quantity:     z.coerce.number().positive().default(1),
  unit_price:   z.coerce.number().min(0).optional().or(z.literal('')),
  payment_type: z.string().default('bhyt'),
  note:         z.string().optional(),
});
type AddForm = z.infer<typeof addSchema>;

// CLS categories
const CLS_CATEGORIES = [
  '-- Tự nhập --',
  'Xét nghiệm máu tổng quát',
  'Xét nghiệm nước tiểu',
  'Siêu âm bụng tổng quát',
  'Siêu âm tim',
  'X-Quang ngực thẳng',
  'Điện tâm đồ (ECG)',
  'Chụp CT Scanner',
  'Chụp MRI',
  'Nội soi dạ dày',
  'Đo mật độ xương',
  'Xét nghiệm đường huyết',
  'Xét nghiệm HbA1c',
  'Xét nghiệm lipid máu',
  'Xét nghiệm chức năng gan',
  'Xét nghiệm chức năng thận',
  'Xét nghiệm HIV',
];

interface Props {
  examId:   number;
  items:    PrescriptionItemResponse[];
  disabled: boolean;
  onChanged: () => void;
}

interface ResultEditing {
  itemId: number;
  result: string;
}

export default function ClsPanel({ examId, items, disabled, onChanged }: Props) {
  const [adding,  setAdding]  = useState(false);
  const [resultEditing, setResultEditing] = useState<ResultEditing | null>(null);
  const [category, setCategory] = useState(CLS_CATEGORIES[0] ?? '');
  const addAsync = useAsync<PrescriptionItemResponse>();
  const delAsync = useAsync<void>();

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm<AddForm>({
    resolver: zodResolver(addSchema),
    defaultValues: { quantity: 1, payment_type: 'bhyt' },
  });

  const onCategoryChange = (cat: string) => {
    setCategory(cat);
    if (cat !== '-- Tự nhập --') setValue('item_name', cat);
  };

  const onAdd = async (data: AddForm) => {
    const res = await addAsync.run(
      examinationApi.addItem(examId, {
        item_type:   'cls',
        item_name:   data.item_name,
        item_code:   data.item_code || undefined,
        unit:        data.unit || undefined,
        quantity:    data.quantity,
        unit_price:  data.unit_price ? Number(data.unit_price) : undefined,
        payment_type: data.payment_type,
      }),
    );
    if (res) {
      toast.success('Đã thêm chỉ định CLS');
      reset(); setAdding(false); setCategory(CLS_CATEGORIES[0] ?? '');
      onChanged();
    } else toast.error(addAsync.error ?? 'Thêm thất bại');
  };

  const onDelete = async (id: number) => {
    await delAsync.run(examinationApi.deleteItem(examId, id));
    toast.success('Đã xoá');
    onChanged();
  };

  const fmtMoney = (v?: number | null) =>
    v !== undefined && v !== null ? v.toLocaleString('vi-VN') + ' ₫' : '';

  // Result status indicator
  const getResultStatus = (item: PrescriptionItemResponse) => {
    // We store result in usage_instruction field for CLS items
    if (item.usage_instruction) return { label: 'Có kết quả', color: '#059669', bg: '#d1fae5' };
    return { label: 'Chờ kết quả', color: '#92400e', bg: '#fef3c7' };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Summary */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ padding: '10px 18px', background: 'var(--clr-primary-light)', borderRadius: 8 }}>
          <span className="text-sm" style={{ color: 'var(--clr-primary-dark)' }}>
            Tổng chỉ định: <strong>{items.length}</strong>
          </span>
        </div>
        <div style={{ padding: '10px 18px', background: '#d1fae5', borderRadius: 8 }}>
          <span className="text-sm" style={{ color: '#065f46' }}>
            Có kết quả: <strong>{items.filter(i => i.usage_instruction).length}</strong>
          </span>
        </div>
        <div style={{ padding: '10px 18px', background: '#fef3c7', borderRadius: 8 }}>
          <span className="text-sm" style={{ color: '#92400e' }}>
            Chờ kết quả: <strong>{items.filter(i => !i.usage_instruction).length}</strong>
          </span>
        </div>
      </div>

      {/* List */}
      {items.length === 0 && !adding ? (
        <EmptyState icon="🔬" title="Chưa có chỉ định CLS" description="Nhấn '+ Thêm chỉ định' để tạo chỉ định cận lâm sàng." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {items.map((item, idx) => {
            const rs = getResultStatus(item);
            const isEditingResult = resultEditing?.itemId === item.id;

            return (
              <div key={item.id} style={{
                background: '#fff', border: '1px solid var(--clr-gray-100)',
                borderRadius: 10, overflow: 'hidden',
              }}>
                {/* Main row */}
                <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{
                    minWidth: 28, height: 28, borderRadius: '50%', background: 'var(--clr-gray-100)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '.8rem', fontWeight: 700, color: 'var(--clr-gray-600)', flexShrink: 0,
                  }}>{idx + 1}</span>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="text-sm font-medium" style={{ color: 'var(--clr-gray-800)' }}>
                      {item.item_name}
                    </div>
                    <div className="flex gap-2 mt-1">
                      {item.item_code && <span className="text-xs text-muted">{item.item_code}</span>}
                      <span className="text-xs text-muted">SL: {item.quantity} {item.unit ?? 'lần'}</span>
                      <Badge variant={item.payment_type}>{item.payment_type.toUpperCase()}</Badge>
                    </div>
                  </div>

                  <div style={{ flexShrink: 0, display: 'flex', gap: 8, alignItems: 'center' }}>
                    {item.total_amount != null && (
                      <span style={{ fontSize: '.85rem', fontWeight: 600, color: 'var(--clr-primary-dark)' }}>
                        {fmtMoney(item.total_amount)}
                      </span>
                    )}
                    <span style={{
                      fontSize: '.72rem', fontWeight: 700, padding: '2px 10px',
                      borderRadius: 9999, background: rs.bg, color: rs.color,
                    }}>
                      {rs.label}
                    </span>
                    {!disabled && (
                      <Button size="sm" variant="ghost"
                        onClick={() => setResultEditing(isEditingResult ? null : { itemId: item.id, result: item.usage_instruction ?? '' })}>
                        📝 {isEditingResult ? 'Đóng' : 'Ghi KQ'}
                      </Button>
                    )}
                    {!disabled && (
                      <button
                        onClick={() => onDelete(item.id)}
                        style={{ background: 'none', border: 'none', color: 'var(--clr-danger)', cursor: 'pointer', padding: '2px 6px', fontSize: '1rem' }}
                        aria-label="Xoá"
                      >✕</button>
                    )}
                  </div>
                </div>

                {/* Result display */}
                {item.usage_instruction && !isEditingResult && (
                  <div style={{
                    padding: '10px 16px', background: '#f0fdf4',
                    borderTop: '1px solid #bbf7d0', fontSize: '.85rem',
                  }}>
                    <span style={{ color: '#166534', fontWeight: 600 }}>KQ: </span>
                    <span style={{ color: '#15803d' }}>{item.usage_instruction}</span>
                  </div>
                )}

                {/* Result editor */}
                {isEditingResult && (
                  <ResultEditor
                    item={item}
                    examId={examId}
                    onSaved={() => { setResultEditing(null); onChanged(); }}
                    onCancel={() => setResultEditing(null)}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add form */}
      {!disabled && (
        adding ? (
          <form onSubmit={handleSubmit(onAdd)}
            style={{ padding: 16, background: 'var(--clr-gray-50)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="form-row form-row-2">
              <Field label="Chọn nhanh dịch vụ CLS">
                <select className="form-input" value={category}
                  onChange={e => onCategoryChange(e.target.value)}>
                  {CLS_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </Field>
              <Field label="Loại chi trả">
                <select {...register('payment_type')} className="form-input">
                  <option value="bhyt">BHYT</option>
                  <option value="fee">Dịch vụ</option>
                  <option value="free">Miễn phí</option>
                </select>
              </Field>
            </div>

            <Field label="Tên chỉ định CLS" required error={errors.item_name?.message}>
              <input {...register('item_name')} className={`form-input${errors.item_name ? ' error' : ''}`}
                placeholder="Tên xét nghiệm / chụp chiếu..." autoFocus />
            </Field>

            <div className="form-row form-row-3">
              <Field label="Mã dịch vụ">
                <input {...register('item_code')} className="form-input" placeholder="Mã (tuỳ chọn)" />
              </Field>
              <Field label="Số lượng" required>
                <input {...register('quantity')} type="number" min={1} className="form-input" />
              </Field>
              <Field label="Đơn giá (VNĐ)">
                <input {...register('unit_price')} type="number" min={0} className="form-input" placeholder="0" />
              </Field>
            </div>

            <div className="flex gap-2">
              <Button type="submit" size="sm" loading={addAsync.loading}>Thêm chỉ định</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => { setAdding(false); reset(); }}>Huỷ</Button>
            </div>
          </form>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>+ Thêm chỉ định CLS</Button>
        )
      )}
    </div>
  );
}

// ── Result Editor ─────────────────────────────────────────────────────────────
function ResultEditor({ item, examId, onSaved, onCancel }: {
  item: PrescriptionItemResponse;
  examId: number;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [result, setResult] = useState(item.usage_instruction ?? '');
  const saveAsync = useAsync<unknown>();

  const handleSave = async () => {
    // Store result in usage_instruction field
    const res = await saveAsync.run(
      examinationApi.deleteItem(examId, item.id).then(() =>
        examinationApi.addItem(examId, {
          item_type:         'cls',
          item_name:         item.item_name,
          item_code:         item.item_code ?? undefined,
          unit:              item.unit ?? undefined,
          quantity:          Number(item.quantity),
          unit_price:        item.unit_price !== null ? Number(item.unit_price) : undefined,
          payment_type:      item.payment_type,
          usage_instruction: result || undefined,
        })
      ),
    );
    if (res !== null) { toast.success('Đã lưu kết quả CLS'); onSaved(); }
    else toast.error('Lưu thất bại');
  };

  return (
    <div style={{ padding: '12px 16px', background: '#fffbeb', borderTop: '1px solid #fde68a' }}>
      <div className="text-xs text-muted" style={{ marginBottom: 6, fontWeight: 600 }}>
        📝 Nhập kết quả CLS — {item.item_name}
      </div>
      <textarea
        className="form-input"
        rows={3}
        value={result}
        placeholder="Nhập kết quả xét nghiệm / chẩn đoán hình ảnh..."
        onChange={e => setResult(e.target.value)}
        autoFocus
      />
      <div className="flex gap-2" style={{ marginTop: 8 }}>
        <Button size="sm" loading={saveAsync.loading} onClick={handleSave}>💾 Lưu kết quả</Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>Huỷ</Button>
      </div>
    </div>
  );
}

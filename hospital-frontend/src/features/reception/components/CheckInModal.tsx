import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { receptionApi } from '@api/reception.api';
import { useAsync } from '@hooks/useAsync';
import { Modal, Button, Field } from '@components/ui';
import type { ReceptionList } from '@/types';

interface Props {
  reception: ReceptionList;
  onClose:   () => void;
  onSuccess: () => void;
}

interface FormValues {
  queue_ticket_id:   string;
  receptionist_name: string;
  internal_note:     string;
}

export default function CheckInModal({ reception, onClose, onSuccess }: Props) {
  const { register, handleSubmit } = useForm<FormValues>();
  const checkInAsync = useAsync<unknown>();

  const onSubmit = async (data: FormValues) => {
    const res = await checkInAsync.run(
      receptionApi.checkIn(reception.id, {
        queue_ticket_id:   data.queue_ticket_id ? Number(data.queue_ticket_id) : null,
        receptionist_name: data.receptionist_name || null,
        internal_note:     data.internal_note || null,
      }),
    );
    if (res !== null) {
      toast.success('Check-in thành công!');
      onSuccess();
    } else {
      toast.error(checkInAsync.error ?? 'Check-in thất bại');
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Check-in — ${reception.patient?.full_name ?? ''}`}
      size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button form="checkin-form" type="submit" loading={checkInAsync.loading}>
            Xác nhận Check-in
          </Button>
        </>
      }
    >
      <form id="checkin-form" onSubmit={handleSubmit(onSubmit)}
        style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div style={{ padding: '12px 16px', background: 'var(--clr-gray-50)', borderRadius: 8, fontSize: '.875rem' }}>
          <div><strong>Phòng khám:</strong> {reception.clinic_room ?? '—'}</div>
          <div><strong>Số khám:</strong> {reception.visit_number ?? '—'}</div>
          <div><strong>Giờ đăng ký:</strong> {reception.visit_time ?? '—'}</div>
        </div>

        <Field label="Số thứ tự hàng chờ (tuỳ chọn)">
          <input {...register('queue_ticket_id')} type="number" className="form-input" placeholder="Để trống nếu không dùng" min={1} />
        </Field>

        <Field label="Nhân viên tiếp đón">
          <input {...register('receptionist_name')} className="form-input" placeholder="Họ tên nhân viên" />
        </Field>

        <Field label="Ghi chú nội bộ">
          <textarea {...register('internal_note')} className="form-input" rows={2} placeholder="Ghi chú (không hiển thị cho bệnh nhân)" />
        </Field>
      </form>
    </Modal>
  );
}

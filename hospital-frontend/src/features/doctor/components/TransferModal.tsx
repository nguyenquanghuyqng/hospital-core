import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import toast from 'react-hot-toast';
import { doctorApi } from '@api/doctor.api';
import { useAsync } from '@hooks/useAsync';
import { Modal, Button, Field } from '@components/ui';
import type { QueueItem } from '@/types';

const CLINIC_ROOMS = ['Phòng 1', 'Phòng 2', 'Phòng 3', 'Phòng 4', 'Phòng Tim Mạch', 'Phòng Nhi'];

const schema = z.object({
  clinic_room: z.string().min(1, 'Vui lòng chọn phòng đích'),
  note:        z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

interface Props { reception: QueueItem; onClose: () => void; onSuccess: () => void }

export default function TransferModal({ reception, onClose, onSuccess }: Props) {
  const transferAsync = useAsync<unknown>();
  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormValues) => {
    const res = await transferAsync.run(
      doctorApi.transfer(reception.id, { clinic_room: data.clinic_room, note: data.note }),
    );
    if (res !== null) {
      toast.success(`Đã chuyển sang ${data.clinic_room}`);
      onSuccess();
    } else {
      toast.error(transferAsync.error ?? 'Chuyển phòng thất bại');
    }
  };

  return (
    <Modal open onClose={onClose} title={`Chuyển phòng — ${reception.patient.full_name}`} size="sm"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Huỷ</Button>
          <Button form="transfer-form" type="submit" loading={transferAsync.loading}>Xác nhận</Button>
        </>
      }
    >
      <form id="transfer-form" onSubmit={handleSubmit(onSubmit)}
        style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <Field label="Phòng khám đích" required error={errors.clinic_room?.message}>
          <select {...register('clinic_room')} className={`form-input${errors.clinic_room ? ' error' : ''}`}>
            <option value="">— Chọn phòng —</option>
            {CLINIC_ROOMS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </Field>
        <Field label="Lý do / ghi chú">
          <textarea {...register('note')} className="form-input" rows={3}
            placeholder="Ghi chú lý do chuyển phòng..." />
        </Field>
      </form>
    </Modal>
  );
}

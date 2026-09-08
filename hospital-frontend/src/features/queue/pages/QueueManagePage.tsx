import { useEffect, useCallback, useState } from 'react';
import toast from 'react-hot-toast';
import { queueApi } from '@api/queue.api';
import { useQueueStore } from '@store/queue.store';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAsync } from '@hooks/useAsync';
import { Button, Card, StatCard, StatusBadge, EmptyState, LoadingOverlay } from '@components/ui';
import { pad, fmtDateTime } from '@lib/utils';
import type { QueueTicket, QueueSummary } from '@/types';

export default function QueueManagePage() {
  const store = useQueueStore();
  const listAsync = useAsync<QueueTicket[]>();
  const callAsync = useAsync<QueueTicket>();
  const [counterNumber, setCounterNumber] = useState<number>(1);

  const loadWaiting = useCallback(() => {
    listAsync.run(queueApi.waiting({ counter_number: counterNumber }))
      .then(list => { if (list) store.setWaiting(list); });
    queueApi.summary({ counter_number: counterNumber })
      .then(s => store.setSummary(s))
      .catch(() => null);
  }, [counterNumber]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { loadWaiting(); }, [loadWaiting]);

  useWebSocket({
    room: 'display',
    onMessage: (type, data) => {
      if (type === 'number_called') {
        const d = data as { ticket_number: number; counter_number: number };
        store.setCurrent({ ticket_number: d.ticket_number } as QueueTicket);
        loadWaiting();
      }
      if (['ticket_created', 'summary_update'].includes(type)) {
        if (type === 'summary_update') store.setSummary(data as QueueSummary);
        loadWaiting();
      }
    },
  });

  const handleCallNext = async () => {
    const t = await callAsync.run(queueApi.callNext(counterNumber));
    if (t) {
      store.setCurrent(t);
      toast.success(`Đã gọi số ${pad(t.ticket_number)}`);
      loadWaiting();
    } else {
      toast.error(callAsync.error ?? 'Không có số nào trong hàng chờ');
    }
  };

  const handleDone = async (id: number) => {
    await queueApi.done(id);
    toast.success('Đã hoàn thành');
    loadWaiting();
  };

  const handleSkip = async (id: number) => {
    await queueApi.skip(id);
    toast.success('Đã bỏ qua');
    loadWaiting();
  };

  const s = store.summary;

  return (
    <div className="page-container">
      {/* Stats */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <StatCard label="Đang chờ"     value={s?.total_waiting ?? 0}  icon="⏳" color="#92400e" bg="#fef3c7" />
        <StatCard label="Đang phục vụ" value={s?.total_serving ?? 0}  icon="🔔" color="#1e40af" bg="#dbeafe" />
        <StatCard label="Số đang gọi"  value={s?.current_number ? pad(s.current_number) : '—'} icon="📢" color="#7c3aed" bg="#ede9fe" />
        <StatCard label="Quầy"         value={counterNumber} icon="🏧" color="#065f46" bg="#d1fae5" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 20 }}>
        {/* Controls */}
        <Card title="Điều khiển quầy">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label className="form-label">Quầy số</label>
              <input
                type="number" min={1} max={20} value={counterNumber}
                className="form-input" style={{ marginTop: 4 }}
                onChange={e => setCounterNumber(Number(e.target.value))}
              />
            </div>

            {store.currentTicket && (
              <div style={{
                padding: '16px', background: 'var(--clr-primary-light)',
                borderRadius: 12, textAlign: 'center',
              }}>
                <div style={{ fontSize: '.75rem', color: 'var(--clr-primary-dark)', marginBottom: 4 }}>Đang phục vụ</div>
                <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--clr-primary)' }}>
                  {pad(store.currentTicket.ticket_number)}
                </div>
              </div>
            )}

            <Button onClick={handleCallNext} loading={callAsync.loading}>
              📢 Gọi số tiếp theo
            </Button>

            {store.currentTicket && (
              <div style={{ display: 'flex', gap: 8 }}>
                <Button variant="secondary" style={{ flex: 1 }}
                  onClick={() => store.currentTicket && handleDone(store.currentTicket.id)}>
                  ✅ Hoàn thành
                </Button>
                <Button variant="ghost" style={{ flex: 1 }}
                  onClick={() => store.currentTicket && handleSkip(store.currentTicket.id)}>
                  ⏭ Bỏ qua
                </Button>
              </div>
            )}
          </div>
        </Card>

        {/* Waiting list */}
        <Card title={`Hàng chờ (${store.waitingList.length} số)`} actions={
          <Button size="sm" variant="ghost" onClick={loadWaiting}>↻ Làm mới</Button>
        }>
          {listAsync.loading && <LoadingOverlay />}
          {!listAsync.loading && store.waitingList.length === 0 && (
            <EmptyState icon="✅" title="Hàng đợi trống" description="Không có số nào đang chờ." />
          )}
          {store.waitingList.length > 0 && (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Số</th>
                    <th>Trạng thái</th>
                    <th>Thời gian</th>
                    <th>Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {store.waitingList.map(t => (
                    <tr key={t.id}>
                      <td>
                        <span style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--clr-primary)' }}>
                          {pad(t.ticket_number)}
                        </span>
                      </td>
                      <td><StatusBadge status={t.status} /></td>
                      <td className="text-xs text-muted">{fmtDateTime(t.created_at)}</td>
                      <td>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => handleDone(t.id)}>✅</Button>
                          <Button size="sm" variant="ghost" onClick={() => handleSkip(t.id)}>⏭</Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

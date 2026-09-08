/**
 * KioskPage — màn hình kiosk lấy số thứ tự.
 * Public page — không cần đăng nhập.
 */
import { useState, useCallback } from 'react';
import { queueApi } from '@api/queue.api';
import { useQueueStore } from '@store/queue.store';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAsync } from '@hooks/useAsync';
import { pad } from '@lib/utils';
import type { QueueTicket, QueueSummary } from '@/types';

export default function KioskPage() {
  const store = useQueueStore();
  const [ticket, setTicket] = useState<QueueTicket | null>(null);
  const takeAsync = useAsync<QueueTicket>();

  // Real-time summary
  useWebSocket({
    room: 'kiosk',
    onMessage: (type, data) => {
      if (type === 'summary_update') store.setSummary(data as QueueSummary);
    },
  });

  const handleTake = useCallback(async () => {
    const t = await takeAsync.run(queueApi.takeTicket({}));
    if (t) { setTicket(t); store.setCurrent(t); }
  }, [takeAsync, store]);

  const handleReset = () => { setTicket(null); store.setCurrent(null); };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg,#0c2340,#0a3d62,#0ea5e9)',
      padding: 24, fontFamily: 'var(--font-sans)',
    }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 48, color: '#fff' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>✚</div>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, lineHeight: 1.2 }}>Phòng Khám Thiện Nhân</h1>
        <p style={{ opacity: .7, marginTop: 6 }}>Lấy số thứ tự tự động</p>
      </div>

      {ticket ? (
        /* Ticket display */
        <div style={{
          background: '#fff', borderRadius: 24, padding: '40px 64px',
          textAlign: 'center', boxShadow: '0 24px 80px rgba(0,0,0,.3)',
          minWidth: 320,
        }}>
          <div style={{ fontSize: '.9rem', color: 'var(--clr-gray-500)', textTransform: 'uppercase', letterSpacing: '.1em', marginBottom: 8 }}>
            Số của bạn
          </div>
          <div style={{
            fontSize: '5rem', fontWeight: 900, lineHeight: 1,
            color: 'var(--clr-primary)', marginBottom: 16,
          }}>
            {pad(ticket.ticket_number)}
          </div>
          {store.summary && (
            <div style={{ fontSize: '.9rem', color: 'var(--clr-gray-500)', marginBottom: 24 }}>
              Đang phục vụ số: <strong style={{ color: 'var(--clr-gray-800)' }}>
                {store.summary.current_number ? pad(store.summary.current_number) : '—'}
              </strong>
              &nbsp;·&nbsp; Còn {Math.max(0, ticket.ticket_number - (store.summary.current_number ?? 0) - 1)} người trước bạn
            </div>
          )}
          <p style={{ fontSize: '.85rem', color: 'var(--clr-gray-400)', marginBottom: 28, lineHeight: 1.6 }}>
            Vui lòng giữ phiếu và chú ý màn hình LED.<br />Khi được gọi vui lòng đến quầy tiếp đón.
          </p>
          <button
            onClick={handleReset}
            style={{
              padding: '10px 28px', borderRadius: 9999, border: '2px solid var(--clr-gray-200)',
              background: 'transparent', cursor: 'pointer', fontSize: '.9rem',
              color: 'var(--clr-gray-600)', fontFamily: 'inherit',
            }}
          >
            Lấy số mới
          </button>
        </div>
      ) : (
        /* Take ticket button */
        <div style={{ textAlign: 'center' }}>
          {store.summary && (
            <div style={{
              background: 'rgba(255,255,255,.12)', backdropFilter: 'blur(12px)',
              borderRadius: 16, padding: '16px 32px', marginBottom: 32, color: '#fff',
              border: '1px solid rgba(255,255,255,.2)',
            }}>
              <span style={{ opacity: .8, marginRight: 12 }}>Đang phục vụ:</span>
              <strong style={{ fontSize: '1.4rem' }}>
                {store.summary.current_number ? pad(store.summary.current_number) : '—'}
              </strong>
              <span style={{ opacity: .5, margin: '0 16px' }}>|</span>
              <span style={{ opacity: .8 }}>Đang chờ:</span>
              <strong style={{ fontSize: '1.4rem', marginLeft: 8 }}>{store.summary.total_waiting}</strong>
            </div>
          )}

          <button
            onClick={handleTake}
            disabled={takeAsync.loading}
            style={{
              width: 200, height: 200, borderRadius: '50%',
              background: takeAsync.loading ? 'rgba(255,255,255,.3)' : '#fff',
              border: 'none', cursor: takeAsync.loading ? 'not-allowed' : 'pointer',
              fontSize: '1.1rem', fontWeight: 700, color: 'var(--clr-primary)',
              boxShadow: '0 8px 40px rgba(0,0,0,.3)',
              transition: 'transform .15s, box-shadow .15s',
              fontFamily: 'var(--font-sans)',
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              gap: 10, margin: '0 auto',
            }}
            onMouseEnter={e => { if (!takeAsync.loading) { (e.currentTarget as HTMLButtonElement).style.transform = 'scale(1.04)'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 12px 48px rgba(0,0,0,.35)'; } }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.transform = 'scale(1)'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 8px 40px rgba(0,0,0,.3)'; }}
          >
            <span style={{ fontSize: '2.5rem' }}>{takeAsync.loading ? '⏳' : '🎫'}</span>
            {takeAsync.loading ? 'Đang lấy...' : 'LẤY SỐ'}
          </button>

          {takeAsync.error && (
            <p style={{ color: '#fca5a5', marginTop: 16, fontSize: '.9rem' }}>
              {takeAsync.error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * DisplayPage — màn hình LED hiển thị số đang được gọi.
 * Public page — không cần đăng nhập.
 */
import { useState, useEffect } from 'react';
import { useWebSocket } from '@hooks/useWebSocket';
import { pad } from '@lib/utils';

interface DisplayState {
  current_number:  number | null;
  counter_number:  number | null;
  previous_number: number | null;
  date:            string;
}

export default function DisplayPage() {
  const [display, setDisplay] = useState<DisplayState>({
    current_number: null, counter_number: null, previous_number: null,
    date: new Date().toLocaleDateString('vi-VN'),
  });
  const [flash, setFlash] = useState(false);
  const [clock, setClock] = useState('');

  // Clock
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // WebSocket
  useWebSocket({
    room: 'display',
    onMessage: (type, data) => {
      if (type === 'number_called') {
        const d = data as { ticket_number: number; counter_number: number };
        setDisplay(prev => ({
          ...prev,
          previous_number: prev.current_number,
          current_number:  d.ticket_number,
          counter_number:  d.counter_number,
        }));
        setFlash(true);
        setTimeout(() => setFlash(false), 1500);
        // Browser beep
        try {
          const ctx = new AudioContext();
          const osc = ctx.createOscillator();
          osc.connect(ctx.destination);
          osc.frequency.value = 880;
          osc.start(); osc.stop(ctx.currentTime + .35);
        } catch { /* ignore */ }
      }
    },
  });

  return (
    <div style={{
      minHeight: '100vh', background: '#0c2340', color: '#fff',
      fontFamily: 'var(--font-sans)', display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 40px', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,.06)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44, height: 44, background: 'var(--clr-primary)', borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.3rem',
          }}>✚</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem' }}>Phòng Khám Thiện Nhân</div>
            <div style={{ fontSize: '.75rem', opacity: .5 }}>Hệ thống quản lý hàng đợi</div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, fontVariantNumeric: 'tabular-nums', letterSpacing: '.05em', color: '#93c5fd' }}>{clock}</div>
          <div style={{ fontSize: '.8rem', opacity: .5 }}>{display.date}</div>
        </div>
      </div>

      {/* Main number */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{ fontSize: '1rem', opacity: .6, textTransform: 'uppercase', letterSpacing: '.15em', marginBottom: 16 }}>
            Số đang được gọi
          </div>
          <div style={{
            fontSize: 'clamp(5rem, 20vw, 13rem)', fontWeight: 900, lineHeight: 1,
            color: flash ? '#fbbf24' : '#38bdf8',
            transition: 'color .3s',
            textShadow: flash ? '0 0 80px rgba(251,191,36,.5)' : '0 0 60px rgba(56,189,248,.3)',
            letterSpacing: '-.02em',
          }}>
            {display.current_number !== null ? pad(display.current_number) : '- - -'}
          </div>
          {display.counter_number && (
            <div style={{ fontSize: '1.2rem', opacity: .7, marginTop: 16 }}>
              Quầy số <strong style={{ color: '#a5f3fc', fontSize: '1.6rem' }}>{display.counter_number}</strong>
            </div>
          )}
        </div>

        {/* Previous */}
        {display.previous_number !== null && (
          <div style={{
            padding: '14px 32px', borderRadius: 12,
            background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.08)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '.8rem', opacity: .5, marginBottom: 4 }}>Số vừa gọi</div>
            <div style={{ fontSize: '2.2rem', fontWeight: 700, opacity: .6 }}>{pad(display.previous_number)}</div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '14px 40px', borderTop: '1px solid rgba(255,255,255,.05)',
        display: 'flex', justifyContent: 'center',
        fontSize: '.8rem', opacity: .4,
      }}>
        Hệ thống quản lý phòng khám Thiện Nhân
      </div>
    </div>
  );
}

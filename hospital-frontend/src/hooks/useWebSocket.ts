/**
 * useWebSocket — reconnecting WebSocket hook.
 * Tiêu chí 12: WebSocket logic không duplicate giữa các màn hình.
 */
import { useEffect, useRef, useCallback } from 'react';

type WSRoom = 'display' | 'kiosk' | 'reception';
type Handler = (data: unknown) => void;

interface UseWebSocketOptions {
  room:      WSRoom;
  onMessage: (type: string, data: unknown) => void;
  enabled?:  boolean;
}

/** WS path prefix — mirrors Vite proxy config (/api → FastAPI) */
const WS_PATH = '/api/v1/queue/ws';

/** Derive ws(s):// base from current page origin — works with Vite proxy & production */
function buildWsBase(): string {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${location.host}${WS_PATH}`;
}

export function useWebSocket({ room, onMessage, enabled = true }: UseWebSocketOptions) {
  const wsRef           = useRef<WebSocket | null>(null);
  const reconnectTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnects      = useRef(0);
  const intentionalClose = useRef(false);
  const onMessageRef    = useRef<Handler>(() => undefined);
  onMessageRef.current  = (raw: unknown) => {
    if (typeof raw !== 'object' || raw === null) return;
    const msg = raw as { type?: string; data?: unknown };
    if (msg.type) onMessage(msg.type, msg.data ?? null);
  };

  const connect = useCallback(() => {
    if (!enabled) return;
    intentionalClose.current = false;
    const ws = new WebSocket(`${buildWsBase()}/${room}`);
    wsRef.current = ws;

    ws.onopen  = () => { reconnects.current = 0; };
    ws.onmessage = ({ data }) => {
      try {
        const parsed: unknown = JSON.parse(data as string);
        if (parsed === 'pong' || (typeof parsed === 'object' && parsed !== null && (parsed as { type?: string }).type === 'pong')) return;
        onMessageRef.current(parsed);
      } catch { /* ignore parse errors */ }
    };
    ws.onerror = () => { /* close event fires next */ };
    ws.onclose = () => {
      if (intentionalClose.current || reconnects.current >= 10) return;
      const delay = Math.min(3000 * (reconnects.current + 1), 15000);
      reconnectTimer.current = setTimeout(() => {
        reconnects.current++;
        connect();
      }, delay);
    };

    // Keepalive ping every 25s
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 25_000);

    ws.addEventListener('close', () => clearInterval(pingInterval));
  }, [room, enabled]);

  useEffect(() => {
    if (!enabled) return;
    connect();
    return () => {
      intentionalClose.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect, enabled]);
}

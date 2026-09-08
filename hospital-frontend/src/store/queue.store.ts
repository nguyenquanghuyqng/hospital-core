/**
 * Queue store — Zustand.
 * Tiêu chí 3: state management có quy tắc — mỗi store = 1 domain.
 */
import { create } from 'zustand';
import type { QueueTicket, QueueSummary } from '@/types';

interface QueueState {
  summary:      QueueSummary | null;
  currentTicket: QueueTicket | null;
  waitingList:  QueueTicket[];
  setSummary:   (s: QueueSummary) => void;
  setCurrent:   (t: QueueTicket | null) => void;
  setWaiting:   (list: QueueTicket[]) => void;
  reset:        () => void;
}

export const useQueueStore = create<QueueState>((set) => ({
  summary:       null,
  currentTicket: null,
  waitingList:   [],
  setSummary:  (summary)      => set({ summary }),
  setCurrent:  (currentTicket) => set({ currentTicket }),
  setWaiting:  (waitingList)  => set({ waitingList }),
  reset: () => set({ summary: null, currentTicket: null, waitingList: [] }),
}));

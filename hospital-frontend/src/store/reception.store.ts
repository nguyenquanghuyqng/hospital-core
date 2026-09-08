import { create } from 'zustand';
import type { ReceptionList } from '@/types';

interface ReceptionState {
  list:      ReceptionList[];
  total:     number;
  page:      number;
  pageSize:  number;
  filters:   { visit_date?: string; status?: string; clinic_room?: string };
  setList:   (items: ReceptionList[], total: number) => void;
  setPage:   (p: number) => void;
  setFilters:(f: Partial<ReceptionState['filters']>) => void;
  reset:     () => void;
}

export const useReceptionStore = create<ReceptionState>((set) => ({
  list:     [],
  total:    0,
  page:     1,
  pageSize: 20,
  filters:  {},
  setList:    (list, total) => set({ list, total }),
  setPage:    (page)        => set({ page }),
  setFilters: (f)           => set((s) => ({ filters: { ...s.filters, ...f }, page: 1 })),
  reset: () => set({ list: [], total: 0, page: 1, filters: {} }),
}));

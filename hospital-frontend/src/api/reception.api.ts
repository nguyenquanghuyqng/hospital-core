import { apiClient } from './client';
import type {
  ReceptionResponse, ReceptionList, ReceptionCreate,
  ReceptionCheckIn, PaginatedResponse,
} from '@/types';

export interface ReceptionListParams {
  visit_date?: string; status?: string; clinic_room?: string;
  page?: number; page_size?: number;
  [key: string]: string | number | boolean | null | undefined;
}

export const receptionApi = {
  /** POST /receptions/scan-cccd */
  scanCccd: (data: { cccd: string }) =>
    apiClient.post<ReceptionResponse>('/receptions/scan-cccd', data),

  /** GET /receptions/stats */
  stats: () =>
    apiClient.get<Record<string, number>>('/receptions/stats'),

  /** GET /receptions */
  list: (params?: ReceptionListParams) =>
    apiClient.get<PaginatedResponse<ReceptionList>>('/receptions', { params }),

  /** GET /receptions/:id */
  get: (id: number) =>
    apiClient.get<ReceptionResponse>(`/receptions/${id}`),

  /** POST /receptions */
  create: (data: ReceptionCreate) =>
    apiClient.post<ReceptionResponse>('/receptions', data),

  /** PUT /receptions/:id */
  update: (id: number, data: Partial<ReceptionCreate>) =>
    apiClient.put<ReceptionResponse>(`/receptions/${id}`, data),

  /** POST /receptions/:id/check-in */
  checkIn: (id: number, data: ReceptionCheckIn) =>
    apiClient.post<ReceptionResponse>(`/receptions/${id}/check-in`, data),

  /** POST /receptions/:id/complete */
  complete: (id: number) =>
    apiClient.post<ReceptionResponse>(`/receptions/${id}/complete`),

  /** POST /receptions/:id/cancel */
  cancel: (id: number) =>
    apiClient.post<ReceptionResponse>(`/receptions/${id}/cancel`),

  /** GET /receptions/clinic-room-stats */
  clinicRoomStats: (visit_date?: string) =>
    apiClient.get<Record<string, unknown>>('/receptions/clinic-room-stats', {
      params: visit_date ? { visit_date } : undefined,
    }),
};

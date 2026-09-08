import { apiClient } from './client';
import type { QueueItem, QueueStatsResponse, VisitStatus } from '@/types';

export const doctorApi = {
  /** GET /doctor/queue */
  queue: (params?: { clinic_room?: string; visit_date?: string }) =>
    apiClient.get<QueueItem[]>('/doctor/queue', { params }),

  /** GET /doctor/queue/stats */
  stats: (params?: { clinic_room?: string; visit_date?: string }) =>
    apiClient.get<QueueStatsResponse>('/doctor/queue/stats', { params }),

  /** PATCH /doctor/receptions/:id/visit-status */
  updateVisitStatus: (id: number, visit_status: VisitStatus) =>
    apiClient.patch<QueueItem>(`/doctor/receptions/${id}/visit-status`, { visit_status }),

  /** POST /doctor/receptions/:id/done */
  completeVisit: (id: number) =>
    apiClient.post<QueueItem>(`/doctor/receptions/${id}/done`),

  /** PATCH /doctor/receptions/:id/transfer */
  transfer: (id: number, data: { clinic_room: string; note?: string }) =>
    apiClient.patch<QueueItem>(`/doctor/receptions/${id}/transfer`, data),
};

import { apiClient } from './client';
import type { QueueTicket, QueueSummary } from '@/types';

export const queueApi = {
  /** POST /queue/ticket — lấy số thứ tự */
  takeTicket: (data: { service_type?: string }) =>
    apiClient.post<QueueTicket>('/queue/ticket', data),

  /** GET /queue/summary */
  summary: (params?: { counter_number?: number }) =>
    apiClient.get<QueueSummary>('/queue/summary', { params }),

  /** GET /queue/waiting */
  waiting: (params?: { counter_number?: number }) =>
    apiClient.get<QueueTicket[]>('/queue/waiting', { params }),

  /** GET /queue/tickets */
  tickets: (params?: { status?: string; skip?: number; limit?: number }) =>
    apiClient.get<QueueTicket[]>('/queue/tickets', { params }),

  /** GET /queue/tickets/:id */
  getTicket: (id: number) =>
    apiClient.get<QueueTicket>(`/queue/tickets/${id}`),

  /** POST /queue/call-next */
  callNext: (counter_number?: number) =>
    apiClient.post<QueueTicket>('/queue/call-next', undefined, {
      params: counter_number !== undefined ? { counter_number } : undefined,
    }),

  /** PATCH /queue/tickets/:id/status */
  updateStatus: (id: number, data: { status: string }) =>
    apiClient.patch<QueueTicket>(`/queue/tickets/${id}/status`, data),

  /** PATCH /queue/tickets/:id/skip */
  skip: (id: number) =>
    apiClient.patch<QueueTicket>(`/queue/tickets/${id}/skip`),

  /** PATCH /queue/tickets/:id/done */
  done: (id: number) =>
    apiClient.patch<QueueTicket>(`/queue/tickets/${id}/done`),
};

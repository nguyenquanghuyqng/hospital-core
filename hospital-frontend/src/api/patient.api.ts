import { apiClient } from './client';
import type { PatientResponse, PatientList, PatientCreate, PaginatedResponse, ReceptionList } from '@/types';

export interface PatientListParams {
  search?: string; page?: number; page_size?: number;
  [key: string]: string | number | boolean | null | undefined;
}

export const patientApi = {
  list: (params?: PatientListParams) =>
    apiClient.get<PaginatedResponse<PatientList>>('/patients', { params }),

  get: (id: number) =>
    apiClient.get<PatientResponse>(`/patients/${id}`),

  getByCccd: (cccd: string) =>
    apiClient.get<PatientResponse>(`/patients/cccd/${cccd}`),

  create: (data: PatientCreate) =>
    apiClient.post<PatientResponse>('/patients', data),

  update: (id: number, data: Partial<PatientCreate>) =>
    apiClient.put<PatientResponse>(`/patients/${id}`, data),

  history: (id: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get<ReceptionList[]>(`/patients/${id}/history`, { params }),
};

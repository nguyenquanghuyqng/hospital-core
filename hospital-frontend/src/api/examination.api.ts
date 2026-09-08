import { apiClient } from './client';
import type { ExaminationResponse, DiagnosisResponse, PrescriptionItemResponse } from '@/types';

export interface ExaminationCreate {
  reception_id: number;
  doctor_id?: number;
  doctor_name?: string;
  clinical_symptoms?: string;
}

export interface DiagnosisCreate {
  icd_code?: string;
  icd_name: string;
  is_primary?: boolean;
  note?: string;
}

export interface PrescriptionItemCreate {
  item_type: 'drug' | 'cls';
  item_name: string;
  item_code?: string;
  unit?: string;
  quantity?: number;
  unit_price?: number;
  usage_instruction?: string;
  payment_type?: string;
}

export const examinationApi = {
  /** POST /examinations */
  create: (data: ExaminationCreate) =>
    apiClient.post<ExaminationResponse>('/examinations', data),

  /** GET /examinations/:id */
  get: (id: number) =>
    apiClient.get<ExaminationResponse>(`/examinations/${id}`),

  /** GET /examinations/by-reception/:id */
  getByReception: (receptionId: number) =>
    apiClient.get<ExaminationResponse>(`/examinations/by-reception/${receptionId}`),

  /** GET /examinations/history/:patientId */
  history: (patientId: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get<ExaminationResponse[]>(`/examinations/history/${patientId}`, { params }),

  /** PUT /examinations/:id */
  update: (id: number, data: Partial<ExaminationCreate> & Record<string, unknown>) =>
    apiClient.put<ExaminationResponse>(`/examinations/${id}`, data),

  /** POST /examinations/:id/save */
  save: (id: number) =>
    apiClient.post<ExaminationResponse>(`/examinations/${id}/save`),

  /** POST /examinations/:id/complete */
  complete: (id: number) =>
    apiClient.post<ExaminationResponse>(`/examinations/${id}/complete`),

  /** POST /examinations/:id/skip */
  skip: (id: number) =>
    apiClient.post<ExaminationResponse>(`/examinations/${id}/skip`),

  /** GET /examinations/:id/cost */
  cost: (id: number) =>
    apiClient.get<Record<string, number>>(`/examinations/${id}/cost`),

  // Diagnoses
  addDiagnosis: (examId: number, data: DiagnosisCreate) =>
    apiClient.post<DiagnosisResponse>(`/examinations/${examId}/diagnoses`, data),

  deleteDiagnosis: (examId: number, diagId: number) =>
    apiClient.delete<void>(`/examinations/${examId}/diagnoses/${diagId}`),

  // Prescription items
  addItem: (examId: number, data: PrescriptionItemCreate) =>
    apiClient.post<PrescriptionItemResponse>(`/examinations/${examId}/items`, data),

  deleteItem: (examId: number, itemId: number) =>
    apiClient.delete<void>(`/examinations/${examId}/items/${itemId}`),
};

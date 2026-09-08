// ─── Enums (mirror app/models/enums.py) ─────────────────────────────────────

export type QueueStatus = 'waiting' | 'calling' | 'serving' | 'done' | 'skipped';
export type ReceptionStatus = 'pending' | 'checked_in' | 'completed' | 'cancelled';
export type VisitStatus = 'waiting' | 'cls' | 'cls_result' | 'revisit' | 'done';
export type ExaminationStatus = 'draft' | 'saved' | 'completed';
export type DispositionType =
  | 'emergency' | 'outpatient' | 'revisit' | 'inpatient_ward'
  | 'inpatient' | 'transfer_out' | 'deceased' | 'transfer_clinic'
  | 'leave_ama' | 'discharged' | 'chronic_script';
export type PaymentType =
  | 'bhyt' | 'fee' | 'request' | 'health' | 'consume'
  | 'under6' | 'vaccine' | 'free' | 'defer';
export type UserRole = 'doctor' | 'nurse' | 'admin';

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  username: string;
  full_name: string | null;
  role: UserRole;
  clinic_room: string | null;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  full_name: string | null;
  role: UserRole;
  clinic_room: string | null;
}

// ─── Patient ─────────────────────────────────────────────────────────────────

export interface PatientList {
  id: number;
  patient_code: string | null;
  full_name: string;
  cccd: string | null;
  date_of_birth: string | null;
  birth_year: number | null;
  gender: 'male' | 'female' | null;
  phone: string | null;
  address_province_name: string | null;
}

export interface PatientResponse extends PatientList {
  cccd_issued_by: string | null;
  cccd_issued_date: string | null;
  occupation: string | null;
  ethnicity_code: string | null;
  ethnicity_name: string | null;
  nationality_code: string | null;
  nationality_name: string | null;
  address_street: string | null;
  address_village: string | null;
  address_ward_code: string | null;
  address_ward_name: string | null;
  address_district_code: string | null;
  address_district_name: string | null;
  address_province_code: string | null;
  address: string | null;
  workplace: string | null;
  email: string | null;
  policy_type: string | null;
  contact_name: string | null;
  contact_address: string | null;
  contact_phone: string | null;
  contact_cccd: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientCreate {
  full_name: string;
  date_of_birth?: string | null;
  birth_year?: number | null;
  gender?: 'male' | 'female' | null;
  cccd?: string | null;
  phone?: string | null;
  address_province_name?: string | null;
  address_district_name?: string | null;
  address_ward_name?: string | null;
  address_street?: string | null;
  [key: string]: unknown;
}

// ─── Queue Ticket ────────────────────────────────────────────────────────────

export interface QueueTicket {
  id: number;
  ticket_number: number;
  counter_number: number | null;
  status: QueueStatus;
  called_at: string | null;
  served_at: string | null;
  service_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface QueueSummary {
  total_waiting: number;
  total_serving: number;
  current_number: number | null;
  counter_number: number | null;
  date: string;
}

// ─── Reception ───────────────────────────────────────────────────────────────

export interface ReceptionList {
  id: number;
  visit_date: string;
  visit_time: string | null;
  status: ReceptionStatus;
  clinic_room: string | null;
  visit_number: number | null;
  priority: number;
  patient_type: string | null;
  subject_name: string | null;
  insurance_number: string | null;
  patient_id: number;
  queue_ticket_id: number | null;
  checked_in_at: string | null;
  patient: PatientList | null;
}

export interface ReceptionResponse extends ReceptionList {
  visit_status: VisitStatus;
  is_appointment: boolean;
  is_online: boolean;
  is_referral: boolean;
  subject_type: string | null;
  insurance_valid_from: string | null;
  insurance_valid_to: string | null;
  initial_registration: string | null;
  referral_note: string | null;
  referral_facility: string | null;
  high_tech_service: boolean;
  insurance_5years: boolean;
  insurance_5years_date: string | null;
  special_status: string | null;
  is_near_poor: boolean;
  is_poor: boolean;
  patient_category: string | null;
  reason: string | null;
  department: string | null;
  doctor_name: string | null;
  completed_at: string | null;
  receptionist_name: string | null;
  internal_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReceptionCreate {
  patient_id?: number | null;
  patient_data?: PatientCreate | null;
  visit_time?: string | null;
  clinic_room?: string | null;
  subject_type?: string | null;
  subject_name?: string | null;
  insurance_number?: string | null;
  priority?: number;
  reason?: string | null;
  is_appointment?: boolean;
  is_online?: boolean;
  is_referral?: boolean;
  [key: string]: unknown;
}

export interface ReceptionCheckIn {
  queue_ticket_id?: number | null;
  receptionist_name?: string | null;
  internal_note?: string | null;
}

// ─── Doctor queue ─────────────────────────────────────────────────────────────

export interface PatientSummary {
  id: number;
  patient_code: string | null;
  full_name: string;
  date_of_birth: string | null;
  birth_year: number | null;
  gender: string | null;
  phone: string | null;
}

export interface QueueItem {
  id: number;
  visit_number: number | null;
  visit_time: string | null;
  visit_status: VisitStatus;
  status: ReceptionStatus;
  patient: PatientSummary;
  patient_type: string | null;
  subject_name: string | null;
  priority: number;
}

export interface QueueStatsResponse {
  clinic_room: string;
  visit_date: string;
  total: number;
  waiting: number;
  cls: number;
  cls_result: number;
  revisit: number;
  done: number;
}

// ─── Examination ─────────────────────────────────────────────────────────────

export interface DiagnosisResponse {
  id: number;
  examination_id: number;
  icd_code: string | null;
  icd_name: string;
  is_primary: boolean;
  note: string | null;
  sort_order: number;
}

export interface PrescriptionItemResponse {
  id: number;
  examination_id: number;
  item_type: 'drug' | 'cls';
  item_code: string | null;
  item_name: string;
  unit: string | null;
  quantity: number;
  unit_price: number | null;
  usage_instruction: string | null;
  payment_type: PaymentType;
  total_amount: number | null;
  bhyt_amount: number | null;
  patient_amount: number | null;
  sort_order: number;
}

export interface ExaminationResponse {
  id: number;
  reception_id: number;
  patient_id: number;
  doctor_id: number | null;
  doctor_name: string | null;
  status: ExaminationStatus;
  exam_date: string;
  exam_start_at: string | null;
  exam_end_at: string | null;
  subject_type: string | null;
  subject_name: string | null;
  insurance_number: string | null;
  clinical_symptoms: string | null;
  complications: string | null;
  disposition: DispositionType | null;
  revisit_days: number | null;
  diagnoses: DiagnosisResponse[];
  prescription_items: PrescriptionItemResponse[];
  created_at: string;
  updated_at: string;
}

// ─── Pagination ───────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── API Error ────────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string | Array<{ msg: string; loc: string[] }>;
  status: number;
}

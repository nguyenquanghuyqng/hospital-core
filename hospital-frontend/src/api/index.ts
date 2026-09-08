/**
 * Barrel export — tất cả API modules.
 * Import từ '@api' thay vì đường dẫn cụ thể.
 */
export { apiClient, tokenStorage } from './client';
export { authApi }       from './auth.api';
export { patientApi }    from './patient.api';
export { receptionApi }  from './reception.api';
export { queueApi }      from './queue.api';
export { doctorApi }     from './doctor.api';
export { examinationApi } from './examination.api';

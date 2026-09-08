/**
 * ROUTES — nguồn duy nhất cho tất cả path constants.
 * Tiêu chí 7: routing tách khỏi component.
 * Tiêu chí 11: không hard-code path ở component.
 */
export const ROUTES = {
  HOME:       '/',
  LOGIN:      '/login',
  FORBIDDEN:  '/403',

  // Reception
  RECEPTION:       '/reception',
  RECEPTION_NEW:   '/reception/new',
  RECEPTION_DETAIL: '/reception/:id',

  // Queue
  KIOSK:    '/kiosk',
  DISPLAY:  '/display',
  QUEUE:    '/queue',

  // Doctor
  DOCTOR:         '/doctor',
  DOCTOR_PATIENT: '/doctor/patient/:receptionId',

  // Examination
  EXAMINATION:        '/examination/:receptionId',
  EXAMINATION_DETAIL: '/examination/view/:id',
} as const;

/** Tạo path có params, e.g. toPath(ROUTES.RECEPTION_DETAIL, { id: 5 }) */
export function toPath(pattern: string, params: Record<string, string | number>): string {
  return Object.entries(params).reduce<string>(
    (acc, [k, v]) => acc.replace(`:${k}`, String(v)),
    pattern,
  );
}

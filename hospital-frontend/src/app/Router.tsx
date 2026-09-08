/**
 * Router — cấu hình routing tập trung với lazy loading.
 * Tiêu chí 5: TypeScript strict.
 * Tiêu chí 7: routing hoàn toàn tách khỏi component.
 */
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from './routes';
import { ProtectedRoute } from '@features/auth/ProtectedRoute';
import { LoadingOverlay } from '@components/ui';
import AppShell from './AppShell';

// ── Lazy imports — tiêu chí 5: code-split per feature ─────────────────────────
const LoginPage         = lazy(() => import('@features/auth/pages/LoginPage'));
const HomePage          = lazy(() => import('@features/auth/pages/HomePage'));
const ForbiddenPage     = lazy(() => import('@features/auth/pages/ForbiddenPage'));

const ReceptionPage     = lazy(() => import('@features/reception/pages/ReceptionPage'));
const ReceptionNewPage  = lazy(() => import('@features/reception/pages/ReceptionNewPage'));
const ReceptionDetailPage = lazy(() => import('@features/reception/pages/ReceptionDetailPage'));

const KioskPage         = lazy(() => import('@features/queue/pages/KioskPage'));
const DisplayPage       = lazy(() => import('@features/queue/pages/DisplayPage'));
const QueueManagePage   = lazy(() => import('@features/queue/pages/QueueManagePage'));

const DoctorQueuePage   = lazy(() => import('@features/doctor/pages/DoctorQueuePage'));
const DoctorPatientPage = lazy(() => import('@features/doctor/pages/DoctorPatientPage'));

const ExaminationPage   = lazy(() => import('@features/examination/pages/ExaminationPage'));

const SuspenseWrap = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<LoadingOverlay />}>{children}</Suspense>
);

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path={ROUTES.LOGIN}   element={<SuspenseWrap><LoginPage /></SuspenseWrap>} />
        <Route path={ROUTES.KIOSK}   element={<SuspenseWrap><KioskPage /></SuspenseWrap>} />
        <Route path={ROUTES.DISPLAY} element={<SuspenseWrap><DisplayPage /></SuspenseWrap>} />
        <Route path={ROUTES.FORBIDDEN} element={<SuspenseWrap><ForbiddenPage /></SuspenseWrap>} />

        {/* Protected — any authenticated user */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path={ROUTES.HOME} element={<SuspenseWrap><HomePage /></SuspenseWrap>} />

            {/* Reception — nurse / admin */}
            <Route element={<ProtectedRoute permission="reception" />}>
              <Route path={ROUTES.RECEPTION}        element={<SuspenseWrap><ReceptionPage /></SuspenseWrap>} />
              <Route path={ROUTES.RECEPTION_NEW}    element={<SuspenseWrap><ReceptionNewPage /></SuspenseWrap>} />
              <Route path={ROUTES.RECEPTION_DETAIL} element={<SuspenseWrap><ReceptionDetailPage /></SuspenseWrap>} />
            </Route>

            {/* Queue management — nurse / admin */}
            <Route element={<ProtectedRoute permission="queue" />}>
              <Route path={ROUTES.QUEUE} element={<SuspenseWrap><QueueManagePage /></SuspenseWrap>} />
            </Route>

            {/* Doctor — doctor / admin */}
            <Route element={<ProtectedRoute permission="doctor" />}>
              <Route path={ROUTES.DOCTOR}         element={<SuspenseWrap><DoctorQueuePage /></SuspenseWrap>} />
              <Route path={ROUTES.DOCTOR_PATIENT} element={<SuspenseWrap><DoctorPatientPage /></SuspenseWrap>} />
            </Route>

            {/* Examination — doctor / admin */}
            <Route element={<ProtectedRoute permission="examination" />}>
              <Route path={ROUTES.EXAMINATION}        element={<SuspenseWrap><ExaminationPage /></SuspenseWrap>} />
              <Route path={ROUTES.EXAMINATION_DETAIL} element={<SuspenseWrap><ExaminationPage /></SuspenseWrap>} />
            </Route>
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to={ROUTES.HOME} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

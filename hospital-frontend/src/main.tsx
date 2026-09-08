import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from '@features/auth/AuthContext';
import AppRouter from './app/Router';
import './assets/globals.css';

const root = document.getElementById('root');
if (!root) throw new Error('Root element #root not found');

createRoot(root).render(
  <StrictMode>
    <AuthProvider>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: { fontFamily: 'var(--font-sans)', fontSize: '.875rem' },
          success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
          error:   { duration: 6000, iconTheme: { primary: '#ef4444', secondary: '#fff' } },
        }}
      />
    </AuthProvider>
  </StrictMode>,
);

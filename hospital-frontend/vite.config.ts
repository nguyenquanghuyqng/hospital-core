import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],

    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@api': path.resolve(__dirname, './src/api'),
        '@components': path.resolve(__dirname, './src/components'),
        '@features': path.resolve(__dirname, './src/features'),
        '@hooks': path.resolve(__dirname, './src/hooks'),
        '@store': path.resolve(__dirname, './src/store'),
        '@lib': path.resolve(__dirname, './src/lib'),
        '@types': path.resolve(__dirname, './src/types'),
      },
    },

    server: {
      port: 5173,
      // Proxy tới FastAPI backend — không hard-code URL trong source
      proxy: {
        '/api': {
          target: env['VITE_API_BASE_URL'] ?? 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: env['VITE_WS_BASE_URL'] ?? 'ws://localhost:8000',
          ws: true,
        },
      },
    },

    build: {
      outDir: '../app/static/dist',
      emptyOutDir: true,
      sourcemap: mode === 'development',
    },
  };
});

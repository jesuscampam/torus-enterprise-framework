/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/**
 * Configuración única de build y de pruebas (ADR-013): Vitest reutiliza esta
 * misma configuración, de modo que los alias y las transformaciones tienen una
 * sola fuente de verdad en vez de duplicarse entre build y tests.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mantener sincronizado con `compilerOptions.paths` de tsconfig.json.
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // El backend TEAF corre por defecto en :8000. El proxy evita CORS en
    // desarrollo y hace que la app use rutas relativas igual que en producción,
    // donde se sirve como estático detrás del mismo origen (ADR-005).
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx', 'src/**/index.ts'],
    },
  },
});

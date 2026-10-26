import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
  build: {
    outDir: 'dist',
    // Recharts è il blocco più pesante: separato per sfruttare la cache del browser.
    rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
    // Il blocco dei grafici (~165 kB gzip) è caricato solo dalle pagine che ne hanno bisogno.
    chunkSizeWarningLimit: 600,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    css: false,
  },
})

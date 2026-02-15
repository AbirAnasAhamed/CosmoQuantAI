import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Prioritize INTERNAL_BACKEND_URL for Docker container-to-container communication
  const backendUrl = process.env.INTERNAL_BACKEND_URL ||
    env.INTERNAL_BACKEND_URL ||
    process.env.VITE_BACKEND_URL ||
    env.VITE_BACKEND_URL ||
    'http://localhost:8000';

  console.log(`🚀 Proxy targeting: ${backendUrl}`);

  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      hmr: {
        clientPort: 3000,
      },
      watch: {
        usePolling: true,
      },
      proxy: {
        // Specific proxy for WebSockets to avoid interfering with regular HTTP calls
        '^/api/v1/.*/ws/.*': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
          ws: true,
        },
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
        '/static': {
          target: backendUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [react()],
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    root: ".",
  };
});
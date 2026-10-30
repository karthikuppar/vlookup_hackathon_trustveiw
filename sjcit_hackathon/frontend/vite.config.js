import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({ plugins: [react()], server: { port: 5173, proxy: { '/auth': 'http://localhost:4000', '/cases': 'http://localhost:4000', '/dashboards': 'http://localhost:4000', '/vico': 'http://localhost:8000' } } })

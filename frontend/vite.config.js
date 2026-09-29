import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Vite's default "localhost" binds IPv6 only (::1) on some Windows
    // setups, so http://127.0.0.1:5173 refused connections. Binding to
    // 127.0.0.1 serves both URLs (browsers fall back to IPv4 for
    // localhost) and keeps the dev server off the local network.
    host: "127.0.0.1",
    port: 5173,
  },
})

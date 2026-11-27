import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { SITE_PATH } from './site.ts'

// https://vite.dev/config/
export default defineConfig({
  base: SITE_PATH,
  plugins: [react()],
})

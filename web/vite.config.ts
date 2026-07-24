import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages project site: https://mattheuscolyn.github.io/oscars-dashboard/
export default defineConfig({
  plugins: [react()],
  base: '/oscars-dashboard/',
})

import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const dir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const repoRoot = path.join(dir, '..')
  const merged = {
    ...loadEnv(mode, repoRoot, ''),
    ...loadEnv(mode, dir, ''),
  }
  const define: Record<string, string> = {}
  for (const [key, value] of Object.entries(merged)) {
    if (key.startsWith('VITE_')) {
      define[`import.meta.env.${key}`] = JSON.stringify(value)
    }
  }
  return {
    define,
    plugins: [react()],
    envDir: dir,
    server: {
      port: 5173,
    },
  }
})

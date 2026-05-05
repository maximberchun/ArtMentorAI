import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const dir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const repoRoot = path.join(dir, '..')
  const srcDir = path.join(dir, 'src')
  const expectedApiFile = path.join(srcDir, 'lib', 'api.ts')
  const expectedSupabaseFile = path.join(srcDir, 'lib', 'supabase.ts')
  const merged = {
    ...loadEnv(mode, repoRoot, ''),
    ...loadEnv(mode, dir, ''),
  }
  // #region agent log
  fetch('http://127.0.0.1:7301/ingest/7d80911c-ea7e-423a-afea-99eba374a490', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'b876b6' },
    body: JSON.stringify({
      sessionId: 'b876b6',
      runId: 'pre-fix',
      hypothesisId: 'H1-H4',
      location: 'frontend/vite.config.ts:16',
      message: 'Vite startup file and env checks',
      data: {
        cwd: process.cwd(),
        dir,
        srcDirExists: fs.existsSync(srcDir),
        expectedApiFile,
        expectedApiFileExists: fs.existsSync(expectedApiFile),
        expectedSupabaseFile,
        expectedSupabaseFileExists: fs.existsSync(expectedSupabaseFile),
        hasApiBaseUrl: Boolean(merged.VITE_API_BASE_URL),
        hasSupabaseUrl: Boolean(merged.VITE_SUPABASE_URL),
      },
      timestamp: Date.now(),
    }),
  }).catch(() => {})
  // #endregion
  const define: Record<string, string> = {}
  for (const [key, value] of Object.entries(merged)) {
    if (key.startsWith('VITE_')) {
      define[`import.meta.env.${key}`] = JSON.stringify(value)
    }
  }
  return {
    define,
    plugins: [
      react(),
      {
        name: 'agent-debug-import-resolver',
        resolveId(source, importer) {
          if (source === '../lib/api' || source === '../lib/supabase') {
            const importerDir = importer ? path.dirname(importer) : null
            const candidateTs = importerDir ? path.resolve(importerDir, `${source}.ts`) : null
            const candidateTsx = importerDir ? path.resolve(importerDir, `${source}.tsx`) : null
            // #region agent log
            fetch('http://127.0.0.1:7301/ingest/7d80911c-ea7e-423a-afea-99eba374a490', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'b876b6' },
              body: JSON.stringify({
                sessionId: 'b876b6',
                runId: 'pre-fix',
                hypothesisId: 'H1-H3',
                location: 'frontend/vite.config.ts:39',
                message: 'Vite resolveId for missing lib import',
                data: {
                  source,
                  importer,
                  importerDir,
                  candidateTs,
                  candidateTsExists: candidateTs ? fs.existsSync(candidateTs) : false,
                  candidateTsx,
                  candidateTsxExists: candidateTsx ? fs.existsSync(candidateTsx) : false,
                },
                timestamp: Date.now(),
              }),
            }).catch(() => {})
            // #endregion
          }
          return null
        },
      },
    ],
    envDir: dir,
    server: {
      port: 5173,
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      globals: true,
    },
  }
})

/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Supabase project URL (Settings → API → Project URL). */
  readonly VITE_SUPABASE_URL: string
  /** Supabase anonymous (public) key — safe in the browser with RLS. */
  readonly VITE_SUPABASE_ANON_KEY: string
  /** FastAPI base URL, no trailing slash (e.g. http://127.0.0.1:8000). */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

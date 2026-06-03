import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

function assertProductionSupabaseHttps(supabaseUrl: string): void {
  if (!import.meta.env.PROD) {
    return
  }
  let parsed: URL
  try {
    parsed = new URL(supabaseUrl)
  } catch {
    throw new Error('VITE_SUPABASE_URL is not a valid URL.')
  }
  if (parsed.protocol === 'http:') {
    throw new Error(
      'VITE_SUPABASE_URL must use https in production builds. Point at your hosted Supabase project URL.',
    )
  }
}

const configured =
  typeof url === 'string' &&
  url.length > 0 &&
  typeof anonKey === 'string' &&
  anonKey.length > 0

if (!configured) {
  console.warn(
    '[ArtMentorAI] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY. ' +
      'Set them in `.env` and restart `npm run dev`.',
  )
} else if (typeof url === 'string') {
  assertProductionSupabaseHttps(url)
}

export const supabase: SupabaseClient | null = configured
  ? createClient(url, anonKey, {
      auth: {
        flowType: 'pkce',
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

import { supabase } from './supabase'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')

function assertProductionUsesHttps(url: string): void {
  if (!import.meta.env.PROD) {
    return
  }
  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    throw new Error('VITE_API_BASE_URL is not a valid URL.')
  }
  if (parsed.protocol === 'http:') {
    throw new Error(
      'VITE_API_BASE_URL must use https in production builds (got http). Use a TLS-terminated API URL.',
    )
  }
}

function requireApiBaseUrl(): string {
  if (!apiBaseUrl) {
    throw new Error('Missing VITE_API_BASE_URL.')
  }
  assertProductionUsesHttps(apiBaseUrl)
  return apiBaseUrl
}

async function getAccessToken(): Promise<string | null> {
  if (!supabase) {
    return null
  }
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken()
  const headers = new Headers(init.headers ?? {})

  if (!(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${requireApiBaseUrl()}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`
    let payload: { detail?: string | { message?: string } | unknown } | null = null
    try {
      payload = (await response.json()) as { detail?: string | { message?: string } | unknown }
    } catch {
      throw new Error(fallback)
    }

    const detail = payload?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (
      detail &&
      typeof detail === 'object' &&
      'message' in detail &&
      typeof (detail as { message?: unknown }).message === 'string'
    ) {
      throw new Error((detail as { message: string }).message)
    }
    throw new Error(fallback)
  }

  return response
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, init)
  return (await response.json()) as T
}

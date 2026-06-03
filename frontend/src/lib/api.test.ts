import { beforeEach, describe, expect, it, vi } from 'vitest'

const getSessionMock = vi.fn()

vi.mock('./supabase', () => ({
  supabase: {
    auth: {
      getSession: getSessionMock,
    },
  },
}))

describe('api client smoke tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
  })

  it('adds auth header when an access token is available', async () => {
    getSessionMock.mockResolvedValue({
      data: { session: { access_token: 'token-123' } },
    })

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { apiFetch } = await import('./api')

    await apiFetch('/health')

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/health',
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    )

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Headers
    expect(headers.get('Authorization')).toBe('Bearer token-123')
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('throws detail string from failed response payload', async () => {
    getSessionMock.mockResolvedValue({ data: { session: null } })

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Invalid payload' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { apiFetch } = await import('./api')

    await expect(apiFetch('/analysis')).rejects.toThrow('Invalid payload')
  })

  it('omits Authorization header when session has no token', async () => {
    getSessionMock.mockResolvedValue({ data: { session: null } })

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const { apiFetch } = await import('./api')

    await apiFetch('/health')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = init.headers as Headers
    expect(headers.get('Authorization')).toBeNull()
    expect(headers.get('Content-Type')).toBe('application/json')
  })

  it('falls back to status text when error body is not JSON', async () => {
    getSessionMock.mockResolvedValue({ data: { session: null } })

    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: async () => {
        throw new Error('not-json')
      },
    })
    vi.stubGlobal('fetch', fetchMock)

    const { apiFetch } = await import('./api')

    await expect(apiFetch('/analysis')).rejects.toThrow('503 Service Unavailable')
  })

  it('propagates network-level fetch failures', async () => {
    getSessionMock.mockResolvedValue({ data: { session: null } })

    const fetchMock = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))
    vi.stubGlobal('fetch', fetchMock)

    const { apiFetch } = await import('./api')

    await expect(apiFetch('/analysis')).rejects.toThrow('Failed to fetch')
  })
})

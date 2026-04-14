import { useState } from 'react'
import { apiJson } from '../lib/api'
import { AuthMe } from '../types/api'

export function HomePage() {
  const [me, setMe] = useState<AuthMe | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadMe() {
    setError(null)
    try {
      const data = await apiJson<AuthMe>('/auth/me')
      setMe(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load auth user.')
      setMe(null)
    }
  }

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Frontend MVP</h2>
      <p className="text-sm text-stone-600">
        This app is wired to the current API contracts for auth, profile, critique, portfolio, and
        history.
      </p>
      <button
        type="button"
        onClick={() => void loadMe()}
        className="rounded-md bg-stone-800 px-3 py-2 text-sm text-white hover:bg-stone-700"
      >
        Validate bearer token via /auth/me
      </button>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {me && (
        <pre className="overflow-x-auto rounded border border-stone-200 bg-white p-3 text-xs">
          {JSON.stringify(me, null, 2)}
        </pre>
      )}
    </section>
  )
}

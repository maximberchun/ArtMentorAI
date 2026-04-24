import { useCallback, useEffect, useState } from 'react'
import { apiJson } from '../lib/api'
import { ProgressMeResponse } from '../types/api'

export function ProgressPage() {
  const [progress, setProgress] = useState<ProgressMeResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadProgress = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await apiJson<ProgressMeResponse>('/progress/me')
      setProgress(data)
    } catch (err) {
      setProgress(null)
      setError(err instanceof Error ? err.message : 'Failed to load progress.')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    void loadProgress()
  }, [loadProgress])

  return (
    <section className="space-y-4">
      <div className="rounded border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Progress dashboard</h2>
          <button
            type="button"
            onClick={() => void loadProgress()}
            className="rounded bg-stone-800 px-3 py-1.5 text-sm text-white"
          >
            Refresh
          </button>
        </div>
        <p className="mt-2 text-sm text-stone-600">Private XP, level, streak, and recent rubric snapshots.</p>
      </div>

      {busy && <p className="text-sm text-stone-600">Loading progress...</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}

      {progress && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <article className="rounded border border-stone-200 bg-white p-3 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Total XP</p>
              <p className="mt-1 text-2xl font-semibold">{progress.total_xp}</p>
            </article>
            <article className="rounded border border-stone-200 bg-white p-3 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Current level</p>
              <p className="mt-1 text-2xl font-semibold">{progress.current_level}</p>
            </article>
            <article className="rounded border border-stone-200 bg-white p-3 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Streak</p>
              <p className="mt-1 text-2xl font-semibold">{progress.streak_count} day(s)</p>
            </article>
          </div>

          <div className="rounded border border-stone-200 bg-white p-4 shadow-sm">
            <h3 className="font-medium">Recent snapshots</h3>
            {progress.recent_snapshots.length === 0 ? (
              <p className="mt-2 text-sm text-stone-600">No snapshots yet. Run at least one critique.</p>
            ) : (
              <ul className="mt-2 space-y-2 text-sm">
                {progress.recent_snapshots.map((snapshot) => (
                  <li key={snapshot.id} className="rounded border border-stone-100 bg-stone-50 p-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{snapshot.rubric_key}</span>
                      <span>
                        {snapshot.aggregate_score !== null
                          ? `Score ${snapshot.aggregate_score.toFixed(1)}`
                          : 'No score'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-stone-500">
                      {snapshot.created_at ? new Date(snapshot.created_at).toLocaleString() : 'Unknown date'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  )
}

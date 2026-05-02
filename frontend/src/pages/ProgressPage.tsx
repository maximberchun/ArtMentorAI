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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Progress Dashboard</h1>
          <p className="mt-1 text-muted-foreground">
            Track your artistic growth and achievements
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadProgress()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          <svg className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Loading */}
      {busy && !progress && (
        <div className="flex items-center justify-center py-16">
          <svg className="h-8 w-8 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}

      {progress && (
        <>
          {/* Stats Cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <article className="relative overflow-hidden rounded-xl border border-border bg-card p-6">
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-primary/10" />
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
                  </svg>
                </div>
                <p className="mt-4 text-3xl font-bold text-foreground">{progress.total_xp.toLocaleString()}</p>
                <p className="mt-1 text-sm text-muted-foreground">Total XP Earned</p>
              </div>
            </article>

            <article className="relative overflow-hidden rounded-xl border border-border bg-card p-6">
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-success/10" />
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10 text-success">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                  </svg>
                </div>
                <p className="mt-4 text-3xl font-bold text-foreground">Level {progress.current_level}</p>
                <p className="mt-1 text-sm text-muted-foreground">Current Level</p>
              </div>
            </article>

            <article className="relative overflow-hidden rounded-xl border border-border bg-card p-6">
              <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-warning/10" />
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10 text-warning">
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z" />
                  </svg>
                </div>
                <p className="mt-4 text-3xl font-bold text-foreground">{progress.streak_count}</p>
                <p className="mt-1 text-sm text-muted-foreground">Day Streak</p>
              </div>
            </article>
          </div>

          {/* Recent Snapshots */}
          <div className="rounded-xl border border-border bg-card p-6">
            <h2 className="mb-4 text-lg font-semibold text-foreground">Recent Rubric Snapshots</h2>

            {progress.recent_snapshots.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12">
                <svg className="h-12 w-12 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
                <p className="mt-4 text-sm text-muted-foreground">No snapshots yet</p>
                <p className="mt-1 text-xs text-muted-foreground">Run at least one critique to see your progress</p>
              </div>
            ) : (
              <div className="space-y-4">
                {progress.recent_snapshots.map((snapshot) => (
                  <article
                    key={snapshot.id}
                    className="rounded-lg border border-border bg-secondary/30 p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium text-foreground">{snapshot.rubric_key}</h3>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {snapshot.created_at
                            ? new Date(snapshot.created_at).toLocaleDateString('en-US', {
                                weekday: 'short',
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                              })
                            : 'Unknown date'}
                        </p>
                      </div>

                      {snapshot.aggregate_score !== null && (
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-secondary">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{ width: `${(snapshot.aggregate_score / 10) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium text-foreground">
                            {snapshot.aggregate_score.toFixed(1)}
                          </span>
                        </div>
                      )}
                    </div>

                    {snapshot.narrative && (
                      <p className="mt-3 text-sm text-muted-foreground">{snapshot.narrative}</p>
                    )}

                    {Object.keys(snapshot.dimension_scores).length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {Object.entries(snapshot.dimension_scores).map(([key, value]) => (
                          <span
                            key={key}
                            className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-xs"
                          >
                            <span className="text-muted-foreground">{key}</span>
                            <span className="font-medium text-foreground">{String(value)}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty State when no progress loaded and not loading */}
      {!progress && !busy && !error && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
          <svg className="h-12 w-12 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          <p className="mt-4 text-sm text-muted-foreground">No progress data available</p>
          <p className="mt-1 text-xs text-muted-foreground">Start critiquing your art to track your growth</p>
        </div>
      )}
    </div>
  )
}

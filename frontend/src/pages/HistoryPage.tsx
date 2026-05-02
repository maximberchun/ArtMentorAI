import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiJson } from '../lib/api'
import { PortfolioHistoryItem } from '../types/api'

export function HistoryPage() {
  const [items, setItems] = useState<PortfolioHistoryItem[]>([])
  const [limit, setLimit] = useState(25)
  const [typeFilter, setTypeFilter] = useState<'all' | 'critique' | 'portfolio_item'>('all')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const query = useMemo(() => {
    const params = new URLSearchParams()
    params.set('limit', String(limit))
    if (typeFilter !== 'all') params.set('type_filter', typeFilter)
    return params.toString()
  }, [limit, typeFilter])

  const loadHistory = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const data = await apiJson<PortfolioHistoryItem[]>(`/portfolio/history/me?${query}`)
      setItems(data)
    } catch (err) {
      setItems([])
      setError(err instanceof Error ? err.message : 'Failed to load history.')
    } finally {
      setBusy(false)
    }
  }, [query])

  useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  function renderCritiqueDetails(item: PortfolioHistoryItem) {
    const orderedIssues = item.prioritized_issues
      .slice()
      .sort((a, b) => (a.priority ?? Number.MAX_SAFE_INTEGER) - (b.priority ?? Number.MAX_SAFE_INTEGER))

    return (
      <div className="mt-4 space-y-4 border-t border-border pt-4">
        {item.rubric_anchors.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium text-foreground">Rubric Anchors</h4>
            <ul className="space-y-1">
              {item.rubric_anchors.map((anchor) => (
                <li key={anchor} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <svg className="mt-1 h-3 w-3 flex-shrink-0 text-primary" fill="currentColor" viewBox="0 0 8 8">
                    <circle cx="4" cy="4" r="3" />
                  </svg>
                  {anchor}
                </li>
              ))}
            </ul>
          </div>
        )}

        {orderedIssues.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium text-foreground">Priority Issues</h4>
            <div className="space-y-2">
              {orderedIssues.map((issue, index) => (
                <div key={`${issue.title}-${issue.priority ?? index}`} className="rounded-lg bg-secondary/50 p-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {issue.priority ?? index + 1}
                    </span>
                    <span className="font-medium text-foreground">{issue.title}</span>
                  </div>
                  {issue.diagnosis && (
                    <p className="mt-1.5 pl-7 text-sm text-muted-foreground">{issue.diagnosis}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {item.root_causes.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium text-foreground">Root Causes</h4>
            <ul className="space-y-1">
              {item.root_causes.map((cause) => (
                <li key={cause} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <svg className="mt-1 h-3 w-3 flex-shrink-0 text-warning" fill="currentColor" viewBox="0 0 8 8">
                    <circle cx="4" cy="4" r="3" />
                  </svg>
                  {cause}
                </li>
              ))}
            </ul>
          </div>
        )}

        {item.targeted_drills.length > 0 && (
          <div>
            <h4 className="mb-2 text-sm font-medium text-foreground">Targeted Drills</h4>
            <div className="space-y-2">
              {item.targeted_drills.map((drill) => (
                <div key={drill.name} className="rounded-lg bg-secondary/50 p-3">
                  <p className="font-medium text-foreground">{drill.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{drill.objective}</p>
                  <p className="mt-1 text-xs text-primary">Check: {drill.success_check}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {item.readiness_gate && (
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Readiness gate:</span> {item.readiness_gate}
          </p>
        )}

        {item.confidence !== null && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Confidence</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${item.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">{(item.confidence * 100).toFixed(0)}%</span>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">History</h1>
        <p className="mt-1 text-muted-foreground">
          Browse your past critiques and portfolio uploads
        </p>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label htmlFor="limit" className="text-sm font-medium text-foreground">Show</label>
            <select
              id="limit"
              className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              value={limit}
              onChange={(ev) => setLimit(Number(ev.target.value))}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="type" className="text-sm font-medium text-foreground">Type</label>
            <select
              id="type"
              className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              value={typeFilter}
              onChange={(ev) => setTypeFilter(ev.target.value as 'all' | 'critique' | 'portfolio_item')}
            >
              <option value="all">All</option>
              <option value="critique">Critiques</option>
              <option value="portfolio_item">Portfolio Items</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => void loadHistory()}
            disabled={busy}
            className="ml-auto inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            <svg className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Loading */}
      {busy && (
        <div className="flex items-center justify-center py-12">
          <svg className="h-8 w-8 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}

      {/* History Items */}
      {!busy && (
        <div className="space-y-4">
          {items.map((item) => (
            <article
              key={item.id}
              className="rounded-xl border border-border bg-card p-4 transition-colors hover:border-border/80"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-medium text-foreground">{item.filename}</h3>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        item.type === 'critique'
                          ? 'bg-primary/10 text-primary'
                          : 'bg-secondary text-muted-foreground'
                      }`}
                    >
                      {item.type === 'critique' ? 'Critique' : 'Portfolio'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(item.timestamp).toLocaleDateString('en-US', {
                      weekday: 'short',
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>

                {item.score !== null && (
                  <div className="flex items-center gap-2 rounded-lg bg-primary px-3 py-1">
                    <span className="text-lg font-bold text-primary-foreground">{item.score}</span>
                    <span className="text-xs text-primary-foreground/80">/10</span>
                  </div>
                )}
              </div>

              {item.summary && (
                <p className="mt-3 text-sm text-muted-foreground">{item.summary}</p>
              )}

              {item.advice && (
                <p className="mt-2 text-sm text-foreground">{item.advice}</p>
              )}

              {item.tags.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {item.type === 'critique' && (
                <>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    className="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80"
                  >
                    {expandedId === item.id ? 'Hide details' : 'Show details'}
                    <svg
                      className={`h-4 w-4 transition-transform ${expandedId === item.id ? 'rotate-180' : ''}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {expandedId === item.id && renderCritiqueDetails(item)}
                </>
              )}
            </article>
          ))}

          {items.length === 0 && !error && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16">
              <svg className="h-12 w-12 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="mt-4 text-sm text-muted-foreground">No history yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Upload portfolio images or request a critique to get started
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

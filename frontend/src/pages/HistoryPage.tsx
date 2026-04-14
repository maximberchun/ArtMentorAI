import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiJson } from '../lib/api'
import { PortfolioHistoryItem } from '../types/api'

export function HistoryPage() {
  const [items, setItems] = useState<PortfolioHistoryItem[]>([])
  const [limit, setLimit] = useState(25)
  const [typeFilter, setTypeFilter] = useState<'all' | 'critique' | 'portfolio_item'>('all')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <section className="space-y-4">
      <div className="rounded border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">History</h2>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <label className="flex items-center gap-1">
            Limit
            <input
              type="number"
              min={1}
              max={500}
              className="w-20 rounded border border-stone-300 px-2 py-1"
              value={limit}
              onChange={(ev) => setLimit(Math.max(1, Math.min(500, Number(ev.target.value) || 1)))}
            />
          </label>
          <label className="flex items-center gap-1">
            Type
            <select
              className="rounded border border-stone-300 px-2 py-1"
              value={typeFilter}
              onChange={(ev) =>
                setTypeFilter(ev.target.value as 'all' | 'critique' | 'portfolio_item')
              }
            >
              <option value="all">All</option>
              <option value="critique">Critique</option>
              <option value="portfolio_item">Portfolio item</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() => void loadHistory()}
            className="rounded bg-stone-800 px-3 py-1.5 text-white"
          >
            Refresh
          </button>
        </div>
      </div>
      {busy && <p className="text-sm text-stone-600">Loading history...</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}
      <div className="space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded border border-stone-200 bg-white p-3 text-sm shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium">{item.filename}</p>
              <span className="rounded bg-stone-100 px-2 py-0.5 text-xs">{item.type}</span>
            </div>
            <p className="mt-1 text-xs text-stone-500">{new Date(item.timestamp).toLocaleString()}</p>
            {item.summary && <p className="mt-2">{item.summary}</p>}
            {item.advice && <p className="mt-2 text-stone-700">{item.advice}</p>}
            {item.score !== null && <p className="mt-2 text-xs">Score: {item.score}/10</p>}
            {item.tags.length > 0 && <p className="mt-1 text-xs text-stone-600">Tags: {item.tags.join(', ')}</p>}
          </article>
        ))}
        {!busy && !error && items.length === 0 && (
          <p className="rounded border border-dashed border-stone-300 bg-white p-4 text-sm text-stone-600">
            No history yet. Upload portfolio images or request a critique.
          </p>
        )}
      </div>
    </section>
  )
}

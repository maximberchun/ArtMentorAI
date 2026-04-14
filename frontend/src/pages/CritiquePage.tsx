import { FormEvent, useState } from 'react'
import { apiFetch } from '../lib/api'
import { AnalysisResponse } from '../types/api'

export function CritiquePage() {
  const [userInput, setUserInput] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)

  async function submitCritique(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const formData = new FormData()
      if (file) formData.append('file', file)
      if (userInput.trim()) formData.append('user_input', userInput)
      const response = await apiFetch('/analysis/critique', {
        method: 'POST',
        body: formData,
      })
      const data = (await response.json()) as AnalysisResponse
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Critique failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-4 rounded border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Critique</h2>
      <form className="space-y-3" onSubmit={submitCritique}>
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          type="file"
          accept="image/*"
          onChange={(ev) => setFile(ev.target.files?.[0] ?? null)}
        />
        <textarea
          className="min-h-24 w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Optional text prompt or context"
          value={userInput}
          onChange={(ev) => setUserInput(ev.target.value)}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-stone-800 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? 'Analyzing...' : 'Submit critique'}
        </button>
      </form>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {result && (
        <div className="rounded border border-stone-200 bg-stone-50 p-3 text-sm">
          <p className="font-medium">Score: {result.score}/10</p>
          <p className="mt-1">{result.summary}</p>
          {result.technical_errors.length > 0 && (
            <ul className="mt-2 list-disc pl-5">
              {result.technical_errors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-stone-700">{result.constructive_advice}</p>
        </div>
      )}
    </section>
  )
}

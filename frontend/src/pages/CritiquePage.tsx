import { FormEvent, useState, useRef } from 'react'
import { Session } from '@supabase/supabase-js'
import { GuestBanner } from '../components/GuestBanner'
import { apiFetch } from '../lib/api'
import { AnalysisResponse } from '../types/api'

type CritiquePageProps = {
  session: Session | null
}

export function CritiquePage({ session }: CritiquePageProps) {
  const isGuest = !session
  const [userInput, setUserInput] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFileChange(selectedFile: File | null) {
    setFile(selectedFile)
    if (selectedFile) {
      const reader = new FileReader()
      reader.onloadend = () => setPreview(reader.result as string)
      reader.readAsDataURL(selectedFile)
    } else {
      setPreview(null)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      handleFileChange(droppedFile)
    }
  }

  async function submitCritique(e: FormEvent) {
    e.preventDefault()
    if (!file) {
      setError('Please upload an image first.')
      return
    }

    setBusy(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
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

  function resetForm() {
    setFile(null)
    setPreview(null)
    setUserInput('')
    setResult(null)
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  return (
    <div className="space-y-8">
      {isGuest && <GuestBanner />}
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-foreground sm:text-3xl">Get Your Art Critiqued</h1>
        <p className="mt-2 text-muted-foreground">
          Upload your artwork and receive detailed AI-powered feedback
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Upload Section */}
        <div className="space-y-6">
          <form onSubmit={submitCritique} className="space-y-6">
            {/* Dropzone */}
            <div
              className={`relative flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all ${
                isDragging
                  ? 'border-primary bg-primary/5'
                  : preview
                    ? 'border-border bg-card'
                    : 'border-border bg-card hover:border-primary/50 hover:bg-primary/5'
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => !preview && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(ev) => handleFileChange(ev.target.files?.[0] ?? null)}
              />

              {preview ? (
                <div className="relative w-full p-4">
                  <img
                    src={preview}
                    alt="Preview"
                    className="mx-auto max-h-80 rounded-lg object-contain"
                  />
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      resetForm()
                    }}
                    className="absolute right-4 top-4 rounded-full bg-background/80 p-2 text-muted-foreground backdrop-blur-sm transition-colors hover:bg-background hover:text-foreground"
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="p-8 text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-foreground">Drop your artwork here</p>
                  <p className="mt-1 text-sm text-muted-foreground">or click to browse files</p>
                  <p className="mt-4 text-xs text-muted-foreground">Supports JPG, PNG, WebP</p>
                </div>
              )}
            </div>

            {/* Context Input */}
            <div>
              <label htmlFor="context" className="mb-2 block text-sm font-medium text-foreground">
                Additional Context <span className="text-muted-foreground">(optional)</span>
              </label>
              <textarea
                id="context"
                className="min-h-24 w-full resize-none rounded-xl border border-border bg-card px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="What were you trying to achieve? Any specific areas you want feedback on?"
                value={userInput}
                onChange={(ev) => setUserInput(ev.target.value)}
              />
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={busy || !file}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? (
                <>
                  <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analyzing...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                  Get Critique
                </>
              )}
            </button>
          </form>
        </div>

        {/* Results Section */}
        <div className="space-y-6">
          {result ? (
            <>
              {/* Score */}
              {result.score !== null && (
                <div className="rounded-2xl border border-border bg-card p-6 text-center">
                  <p className="text-sm font-medium text-muted-foreground">Overall Score</p>
                  <div className="mt-2 flex items-center justify-center gap-2">
                    <span className="text-5xl font-bold text-foreground">{result.score}</span>
                    <span className="text-2xl text-muted-foreground">/10</span>
                  </div>
                  <div className="mt-3 flex items-center justify-center gap-4 text-sm">
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 ${
                      result.readiness_gate === 'pass' 
                        ? 'bg-green-500/10 text-green-500' 
                        : 'bg-yellow-500/10 text-yellow-500'
                    }`}>
                      {result.readiness_gate === 'pass' ? 'Ready to Progress' : 'Keep Practicing'}
                    </span>
                    <span className="text-muted-foreground">
                      {(result.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                </div>
              )}

              {/* Prioritized Issues */}
              {result.prioritized_issues.length > 0 && (
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
                    <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
                    </svg>
                    Areas for Improvement
                  </h3>
                  <div className="space-y-4">
                    {result.prioritized_issues
                      .slice()
                      .sort((a, b) => a.priority - b.priority)
                      .map((issue, index) => (
                        <div key={index} className="flex gap-4 rounded-xl bg-secondary/50 p-4">
                          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-sm font-semibold text-primary">
                            {index + 1}
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{issue.title}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{issue.diagnosis}</p>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Root Causes */}
              {result.root_causes.length > 0 && (
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
                    <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
                    </svg>
                    Root Causes
                  </h3>
                  <ul className="space-y-2">
                    {result.root_causes.map((cause, index) => (
                      <li key={index} className="flex items-start gap-3 text-sm text-muted-foreground">
                        <svg className="mt-1 h-4 w-4 flex-shrink-0 text-primary" fill="currentColor" viewBox="0 0 8 8">
                          <circle cx="4" cy="4" r="3" />
                        </svg>
                        {cause}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Targeted Drills */}
              {result.targeted_drills.length > 0 && (
                <div className="rounded-2xl border border-border bg-card p-6">
                  <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-foreground">
                    <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                    </svg>
                    Recommended Practice
                  </h3>
                  <div className="space-y-3">
                    {result.targeted_drills.map((drill, index) => (
                      <div key={index} className="rounded-xl bg-secondary/50 p-4">
                        <p className="font-medium text-foreground">{drill.name}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{drill.objective}</p>
                        {drill.duration_minutes && (
                          <p className="mt-2 text-xs text-muted-foreground">
                            Estimated time: {drill.duration_minutes} minutes
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* New Critique Button */}
              <button
                type="button"
                onClick={resetForm}
                className="w-full rounded-xl border border-border bg-secondary px-6 py-3 text-sm font-semibold text-secondary-foreground transition-colors hover:bg-border"
              >
                Critique Another Artwork
              </button>
            </>
          ) : (
            <div className="flex h-full min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-8 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary text-muted-foreground">
                <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-foreground">Your critique will appear here</h3>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Upload an artwork and click &quot;Get Critique&quot; to receive detailed AI-powered feedback
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

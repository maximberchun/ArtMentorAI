import { FormEvent, useState, useRef } from 'react'
import { apiFetch, apiJson } from '../lib/api'
import { AnalysisResponse, ConversationInfo, ConversationMessage } from '../types/api'

export function CritiquePage() {
  const [userInput, setUserInput] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [conversation, setConversation] = useState<ConversationInfo | null>(null)
  const [messages, setMessages] = useState<ConversationMessage[]>([])
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

  async function createConversation() {
    setCreatingConversation(true)
    setError(null)
    try {
      const created = await apiJson<ConversationInfo>('/analysis/conversations', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      setConversation(created)
      setMessages([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation.')
    } finally {
      setCreatingConversation(false)
    }
  }

  async function refreshConversationMessages(conversationId: string) {
    setLoadingMessages(true)
    try {
      const data = await apiJson<ConversationMessage[]>(
        `/analysis/conversations/${conversationId}/messages`
      )
      setMessages(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation messages.')
    } finally {
      setLoadingMessages(false)
    }
  }

  async function submitCritique(e: FormEvent) {
    e.preventDefault()
    if (!file && !userInput.trim()) {
      setError('Provide at least an image or a text prompt before submitting.')
      setResult(null)
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const formData = new FormData()
      if (file) formData.append('file', file)
      if (userInput.trim()) formData.append('user_input', userInput)
      if (conversation?.id) formData.append('conversation_id', conversation.id)
      const response = await apiFetch('/analysis/critique', {
        method: 'POST',
        body: formData,
      })
      const data = (await response.json()) as AnalysisResponse
      setResult(data)
      if (conversation?.id) {
        await refreshConversationMessages(conversation.id)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Critique failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Art Critique</h1>
        <p className="mt-1 text-muted-foreground">
          Upload your artwork and receive detailed AI-powered feedback
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Upload Section */}
        <div className="space-y-6">
          {/* Conversation Panel */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void createConversation()}
                disabled={creatingConversation}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                {creatingConversation ? 'Starting...' : 'New Conversation'}
              </button>

              {conversation && (
                <>
                  <span className="rounded-lg bg-secondary px-3 py-1.5 text-xs font-medium text-muted-foreground">
                    Thread: {conversation.id.slice(0, 8)}...
                  </span>
                  <button
                    type="button"
                    onClick={() => void refreshConversationMessages(conversation.id)}
                    disabled={loadingMessages}
                    className="rounded-lg border border-border bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground transition-colors hover:bg-border disabled:opacity-50"
                  >
                    {loadingMessages ? 'Refreshing...' : 'Refresh'}
                  </button>
                </>
              )}
            </div>

            {!conversation && (
              <p className="mt-3 text-xs text-muted-foreground">
                Start a conversation to maintain context between critiques
              </p>
            )}
          </div>

          {/* Upload Form */}
          <form className="space-y-4" onSubmit={submitCritique}>
            <div
              className={`relative rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
                isDragging
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground'
              }`}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              {preview ? (
                <div className="space-y-4">
                  <img
                    src={preview}
                    alt="Preview"
                    className="mx-auto max-h-64 rounded-lg object-contain"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      handleFileChange(null)
                      if (fileInputRef.current) fileInputRef.current.value = ''
                    }}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    Remove image
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                    </svg>
                  </div>
                  <div>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-sm font-medium text-primary hover:text-primary/80"
                    >
                      Upload your artwork
                    </button>
                    <p className="mt-1 text-xs text-muted-foreground">
                      or drag and drop here
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    PNG, JPG, GIF up to 10MB
                  </p>
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(ev) => handleFileChange(ev.target.files?.[0] ?? null)}
              />
            </div>

            <div>
              <label htmlFor="context" className="mb-1.5 block text-sm font-medium text-foreground">
                Additional context (optional)
              </label>
              <textarea
                id="context"
                className="min-h-28 w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="Add any context about your artwork, specific areas you want feedback on, or questions..."
                value={userInput}
                onChange={(ev) => setUserInput(ev.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {busy ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Analyzing...
                </span>
              ) : (
                'Get Critique'
              )}
            </button>
          </form>

          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        {/* Results Section */}
        <div className="space-y-6">
          {result && (
            <div className="rounded-xl border border-border bg-card p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-foreground">Critique Results</h2>
                {result.score !== null && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Score</span>
                    <span className="rounded-lg bg-primary px-3 py-1 text-lg font-bold text-primary-foreground">
                      {result.score}/10
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                {result.rubric_anchors.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-foreground">Rubric Anchors</h3>
                    <ul className="space-y-1">
                      {result.rubric_anchors.map((item) => (
                        <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <svg className="mt-1 h-3 w-3 flex-shrink-0 text-primary" fill="currentColor" viewBox="0 0 8 8">
                            <circle cx="4" cy="4" r="3" />
                          </svg>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.prioritized_issues.length > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-medium text-foreground">Priority Issues</h3>
                    <div className="space-y-3">
                      {result.prioritized_issues
                        .slice()
                        .sort((a, b) => a.priority - b.priority)
                        .map((item) => (
                          <div
                            key={`${item.title}-${item.priority}`}
                            className="rounded-lg border border-border bg-secondary/50 p-4"
                          >
                            <div className="flex items-center gap-2">
                              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                                {item.priority}
                              </span>
                              <h4 className="font-medium text-foreground">{item.title}</h4>
                            </div>
                            <p className="mt-2 text-sm text-muted-foreground">{item.diagnosis}</p>
                          </div>
                        ))}
                    </div>
                  </div>
                )}

                {result.root_causes.length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-foreground">Root Causes</h3>
                    <ul className="space-y-1">
                      {result.root_causes.map((cause) => (
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

                {result.targeted_drills.length > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-medium text-foreground">Recommended Drills</h3>
                    <div className="space-y-2">
                      {result.targeted_drills.map((drill) => (
                        <div key={drill.name} className="rounded-lg border border-border bg-secondary/50 p-3">
                          <h4 className="font-medium text-foreground">{drill.name}</h4>
                          <p className="mt-1 text-sm text-muted-foreground">{drill.objective}</p>
                          <p className="mt-1 text-xs text-primary">Success check: {drill.success_check}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between border-t border-border pt-4">
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">Readiness:</span> {result.readiness_gate}
                  </p>
                  <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                    {(result.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Conversation Messages */}
          {conversation && messages.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-6">
              <h2 className="mb-4 text-lg font-semibold text-foreground">Conversation History</h2>
              <div className="space-y-3">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-primary/10 border border-primary/20'
                        : 'bg-secondary'
                    }`}
                  >
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {message.role}
                    </p>
                    <p className="whitespace-pre-wrap text-sm text-foreground">{message.content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!result && !conversation && (
            <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-border">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
                </svg>
                <p className="mt-2 text-sm text-muted-foreground">
                  Upload artwork to receive AI critique
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

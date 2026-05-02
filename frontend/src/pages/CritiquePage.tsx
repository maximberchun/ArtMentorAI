import { FormEvent, useState } from 'react'
import { apiFetch, apiJson } from '../lib/api'
import { AnalysisResponse, ConversationInfo, ConversationMessage } from '../types/api'

export function CritiquePage() {
  const [userInput, setUserInput] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [conversation, setConversation] = useState<ConversationInfo | null>(null)
  const [messages, setMessages] = useState<ConversationMessage[]>([])

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
    <section className="space-y-4 rounded border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Critique</h2>
      <div className="rounded border border-stone-200 bg-stone-50 p-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void createConversation()}
            disabled={creatingConversation}
            className="rounded bg-stone-700 px-3 py-1.5 text-xs text-white disabled:opacity-50"
          >
            {creatingConversation ? 'Starting...' : 'Start conversation'}
          </button>
          {conversation && (
            <>
              <span className="text-stone-700">Thread: {conversation.id}</span>
              <button
                type="button"
                onClick={() => void refreshConversationMessages(conversation.id)}
                disabled={loadingMessages}
                className="rounded border border-stone-300 bg-white px-2 py-1 text-xs text-stone-700 disabled:opacity-50"
              >
                {loadingMessages ? 'Refreshing...' : 'Refresh messages'}
              </button>
            </>
          )}
        </div>
        {!conversation && (
          <p className="mt-2 text-xs text-stone-600">
            Start a conversation to keep short-term context between critiques.
          </p>
        )}
      </div>
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
          {result.score === null ? (
            <p className="font-medium text-stone-600">No score (text-only critique)</p>
          ) : (
            <p className="font-medium">Score: {result.score}/10</p>
          )}
          {result.rubric_anchors.length > 0 && (
            <ul className="mt-2 list-disc pl-5">
              {result.rubric_anchors.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
          {result.prioritized_issues.length > 0 && (
            <div className="mt-3 space-y-2">
              {result.prioritized_issues
                .slice()
                .sort((a, b) => a.priority - b.priority)
                .map((item) => (
                  <div key={`${item.title}-${item.priority}`}>
                    <p className="font-medium">
                      {item.priority}. {item.title}
                    </p>
                    <p className="text-stone-700">{item.diagnosis}</p>
                  </div>
                ))}
            </div>
          )}
          {result.root_causes.length > 0 && (
            <div className="mt-3">
              <p className="font-medium">Root causes</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {result.root_causes.map((cause) => (
                  <li key={cause}>{cause}</li>
                ))}
              </ul>
            </div>
          )}
          {result.targeted_drills.length > 0 && (
            <div className="mt-3">
              <p className="font-medium">Targeted drills</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">
                {result.targeted_drills.map((drill) => (
                  <li key={drill.name}>
                    <span className="font-medium">{drill.name}:</span> {drill.objective} (Check:{' '}
                    {drill.success_check})
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-2 text-stone-700">Readiness gate: {result.readiness_gate}</p>
          <p className="text-xs text-stone-500">
            Confidence: {(result.confidence * 100).toFixed(0)}%
          </p>
        </div>
      )}
      {conversation && (
        <div className="rounded border border-stone-200 bg-white p-3 text-sm">
          <h3 className="font-medium">Conversation</h3>
          {messages.length === 0 ? (
            <p className="mt-2 text-stone-600">No messages yet.</p>
          ) : (
            <div className="mt-2 space-y-2">
              {messages.map((message) => (
                <div key={message.id} className="rounded border border-stone-200 bg-stone-50 p-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-stone-600">
                    {message.role}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}

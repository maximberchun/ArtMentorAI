import { FormEvent, useState, useRef, useEffect } from 'react'
import { apiFetch, apiJson } from '../lib/api'
import { isTextOnlyCritiqueIntent } from '../lib/conversationIntent'
import { AnalysisResponse, ConversationChatResponse, ConversationInfo } from '../types/api'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  image?: string
  timestamp: Date
  analysis?: AnalysisResponse
  /** Assistant turn shape; default critique for backward compatibility in UI. */
  assistantKind?: 'critique' | 'chat'
}

export function ConversationPage() {
  const [userInput, setUserInput] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversation, setConversation] = useState<ConversationInfo | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`
    }
  }, [userInput])

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

  async function ensureConversation(): Promise<string> {
    if (conversation?.id) return conversation.id
    
    try {
      const created = await apiJson<ConversationInfo>('/analysis/conversations', {
        method: 'POST',
        body: JSON.stringify({}),
      })
      setConversation(created)
      return created.id
    } catch {
      throw new Error('Failed to create conversation')
    }
  }

  async function submitMessage(e: FormEvent) {
    e.preventDefault()
    if (!file && !userInput.trim()) {
      setError('Please provide an image or a message.')
      return
    }

    setBusy(true)
    setError(null)

    // Add user message to chat immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: userInput.trim() || 'Please critique this artwork',
      image: preview || undefined,
      timestamp: new Date(),
    }
    setChatMessages(prev => [...prev, userMessage])

    // Clear input immediately for better UX
    const currentInput = userInput
    const currentFile = file
    setUserInput('')
    setFile(null)
    setPreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''

    try {
      const conversationId = await ensureConversation()

      const useCritique =
        currentFile !== null ||
        (currentInput.trim().length > 0 && isTextOnlyCritiqueIntent(currentInput))

      if (!useCritique && currentInput.trim()) {
        const chatPayload = await apiJson<ConversationChatResponse>('/analysis/chat', {
          method: 'POST',
          body: JSON.stringify({
            message: currentInput.trim(),
            conversation_id: conversationId,
          }),
        })
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: chatPayload.reply,
          timestamp: new Date(),
          assistantKind: 'chat',
        }
        setChatMessages(prev => [...prev, assistantMessage])
      } else {
        const formData = new FormData()
        if (currentFile) formData.append('file', currentFile)
        if (currentInput.trim()) formData.append('user_input', currentInput)
        formData.append('conversation_id', conversationId)

        const response = await apiFetch('/analysis/critique', {
          method: 'POST',
          body: formData,
        })
        const data = (await response.json()) as AnalysisResponse

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: formatCritiqueResponse(data),
          timestamp: new Date(),
          analysis: data,
          assistantKind: 'critique',
        }
        setChatMessages(prev => [...prev, assistantMessage])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message.')
      // Remove the optimistic user message if request failed
      setChatMessages(prev => prev.filter(m => m.id !== userMessage.id))
    } finally {
      setBusy(false)
    }
  }

  function formatCritiqueResponse(data: AnalysisResponse): string {
    let response = ''

    if (data.score !== null) {
      response += `**Overall Score: ${data.score}/10**\n\n`
    }

    if (data.prioritized_issues.length > 0) {
      response += `**Key Areas for Improvement:**\n`
      data.prioritized_issues
        .slice()
        .sort((a, b) => a.priority - b.priority)
        .forEach((issue, index) => {
          response += `${index + 1}. **${issue.title}**: ${issue.diagnosis}\n`
        })
      response += '\n'
    }

    if (data.root_causes.length > 0) {
      response += `**Root Causes:**\n`
      data.root_causes.forEach(cause => {
        response += `- ${cause}\n`
      })
      response += '\n'
    }

    if (data.targeted_drills.length > 0) {
      response += `**Recommended Practice:**\n`
      data.targeted_drills.forEach(drill => {
        response += `- **${drill.name}**: ${drill.objective}\n`
      })
      response += '\n'
    }

    response += `*Readiness: ${data.readiness_gate} | Confidence: ${(data.confidence * 100).toFixed(0)}%*`

    return response
  }

  function startNewConversation() {
    setConversation(null)
    setChatMessages([])
    setError(null)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!busy && (userInput.trim() || file)) {
        submitMessage(e as unknown as FormEvent)
      }
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Art Conversation</h1>
          <p className="text-sm text-muted-foreground">
            {conversation ? `Session: ${conversation.id.slice(0, 8)}...` : 'Start a new conversation'}
          </p>
        </div>
        {chatMessages.length > 0 && (
          <button
            type="button"
            onClick={startNewConversation}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary px-3 py-2 text-sm font-medium text-secondary-foreground transition-colors hover:bg-border"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Chat
          </button>
        )}
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto py-4">
        {chatMessages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
            </div>
            <h2 className="mb-2 text-lg font-semibold text-foreground">Start a Conversation</h2>
            <p className="max-w-md text-sm text-muted-foreground">
              Chat with the AI about your artwork. Upload images, ask questions, and get ongoing feedback in a natural conversation.
            </p>
            <div className="mt-6 grid gap-2 text-left">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <svg className="h-4 w-4 text-primary" fill="currentColor" viewBox="0 0 8 8">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                Drop an image or use the attachment button
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <svg className="h-4 w-4 text-primary" fill="currentColor" viewBox="0 0 8 8">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                Ask follow-up questions about feedback
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <svg className="h-4 w-4 text-primary" fill="currentColor" viewBox="0 0 8 8">
                  <circle cx="4" cy="4" r="3" />
                </svg>
                Share multiple artworks in one session
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {chatMessages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'border border-border bg-card'
                  }`}
                >
                  {message.image && (
                    <img
                      src={message.image}
                      alt="Uploaded artwork"
                      className="mb-3 max-h-64 rounded-lg object-contain"
                    />
                  )}
                  <div className={`text-sm leading-relaxed ${message.role === 'assistant' ? 'prose prose-sm prose-invert max-w-none' : ''}`}>
                    {message.role === 'assistant' ? (
                      <FormattedMessage content={message.content} />
                    ) : (
                      <p>{message.content}</p>
                    )}
                  </div>
                  <p className={`mt-2 text-xs ${message.role === 'user' ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}

            {busy && (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-border bg-card px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="flex gap-1">
                      <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '0ms' }} />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '150ms' }} />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Image Preview */}
      {preview && (
        <div className="mb-3 flex items-center gap-3 rounded-lg border border-border bg-card p-3">
          <img src={preview} alt="Preview" className="h-16 w-16 rounded-lg object-cover" />
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">{file?.name}</p>
            <p className="text-xs text-muted-foreground">
              {file && (file.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              handleFileChange(null)
              if (fileInputRef.current) fileInputRef.current.value = ''
            }}
            className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Input Area */}
      <form
        className={`flex items-end gap-3 rounded-xl border-2 bg-card p-3 transition-colors ${
          isDragging ? 'border-primary bg-primary/5' : 'border-border'
        }`}
        onSubmit={submitMessage}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(ev) => handleFileChange(ev.target.files?.[0] ?? null)}
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          title="Attach image"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
          </svg>
        </button>

        <textarea
          ref={textareaRef}
          className="max-h-36 min-h-10 flex-1 resize-none bg-transparent py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          placeholder={preview ? 'Add context about your artwork...' : 'Type a message or drop an image...'}
          value={userInput}
          onChange={(ev) => setUserInput(ev.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />

        <button
          type="submit"
          disabled={busy || (!userInput.trim() && !file)}
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          title="Send"
        >
          {busy ? (
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          )}
        </button>
      </form>

      <p className="mt-2 text-center text-xs text-muted-foreground">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  )
}

// Component to render formatted markdown-like content
function FormattedMessage({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        // Handle bold text with **
        const formattedLine = line.split(/(\*\*[^*]+\*\*)/).map((part, i) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={i} className="font-semibold text-foreground">
                {part.slice(2, -2)}
              </strong>
            )
          }
          // Handle italic text with *
          return part.split(/(\*[^*]+\*)/).map((subPart, j) => {
            if (subPart.startsWith('*') && subPart.endsWith('*') && !subPart.startsWith('**')) {
              return (
                <em key={`${i}-${j}`} className="italic text-muted-foreground">
                  {subPart.slice(1, -1)}
                </em>
              )
            }
            return subPart
          })
        })

        if (line.trim() === '') {
          return <div key={index} className="h-2" />
        }

        if (line.startsWith('- ')) {
          return (
            <div key={index} className="flex items-start gap-2 text-foreground">
              <svg className="mt-1.5 h-2 w-2 flex-shrink-0 text-primary" fill="currentColor" viewBox="0 0 8 8">
                <circle cx="4" cy="4" r="3" />
              </svg>
              <span>{formattedLine}</span>
            </div>
          )
        }

        if (/^\d+\.\s/.test(line)) {
          const [num, ...rest] = line.split(/\.\s/)
          return (
            <div key={index} className="flex items-start gap-2 text-foreground">
              <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-medium text-primary">
                {num}
              </span>
              <span>{rest.join('. ')}</span>
            </div>
          )
        }

        return (
          <p key={index} className="text-foreground">
            {formattedLine}
          </p>
        )
      })}
    </div>
  )
}

import { FormEvent, useState, useRef } from 'react'
import { apiFetch } from '../lib/api'
import { UploadResponse } from '../types/api'

export function PortfolioPage() {
  const [tags, setTags] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [previews, setPreviews] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function handleFilesChange(selectedFiles: File[]) {
    setFiles(selectedFiles)
    const newPreviews: string[] = []
    selectedFiles.forEach((file) => {
      const reader = new FileReader()
      reader.onloadend = () => {
        newPreviews.push(reader.result as string)
        if (newPreviews.length === selectedFiles.length) {
          setPreviews([...newPreviews])
        }
      }
      reader.readAsDataURL(file)
    })
    if (selectedFiles.length === 0) setPreviews([])
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const droppedFiles = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith('image/')
    )
    if (droppedFiles.length > 0) {
      handleFilesChange(droppedFiles)
    }
  }

  function removeFile(index: number) {
    const newFiles = files.filter((_, i) => i !== index)
    const newPreviews = previews.filter((_, i) => i !== index)
    setFiles(newFiles)
    setPreviews(newPreviews)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function upload(e: FormEvent) {
    e.preventDefault()
    if (files.length === 0) {
      setMessage({ type: 'error', text: 'Select at least one image.' })
      return
    }
    setBusy(true)
    setMessage(null)
    try {
      const formData = new FormData()
      for (const file of files) {
        formData.append('files', file)
      }
      if (tags.trim()) {
        formData.append('tags', tags)
      }
      const response = await apiFetch('/portfolio/upload', {
        method: 'POST',
        body: formData,
      })
      const data = (await response.json()) as UploadResponse
      setMessage({ type: 'success', text: `Successfully uploaded ${data.ids.length} image(s) to your portfolio.` })
      setFiles([])
      setPreviews([])
      setTags('')
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Upload failed.' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Portfolio</h1>
        <p className="mt-1 text-muted-foreground">
          Upload and organize your artwork collection
        </p>
      </div>

      <div className="rounded-xl border border-border bg-card p-6">
        <form className="space-y-6" onSubmit={upload}>
          {/* Drop Zone */}
          <div
            className={`relative rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
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
            {previews.length > 0 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
                  {previews.map((preview, index) => (
                    <div key={index} className="group relative">
                      <img
                        src={preview}
                        alt={`Preview ${index + 1}`}
                        className="aspect-square w-full rounded-lg object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-sm font-medium text-primary hover:text-primary/80"
                >
                  Add more images
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
                  <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                  </svg>
                </div>
                <div>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-sm font-medium text-primary hover:text-primary/80"
                  >
                    Click to upload
                  </button>
                  <p className="mt-1 text-sm text-muted-foreground">
                    or drag and drop your artwork
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  PNG, JPG, GIF up to 10MB each
                </p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(ev) => handleFilesChange(Array.from(ev.target.files ?? []))}
            />
          </div>

          {/* Tags Input */}
          <div>
            <label htmlFor="tags" className="mb-1.5 block text-sm font-medium text-foreground">
              Tags
            </label>
            <input
              id="tags"
              className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="e.g., portrait, sketch, digital (comma separated)"
              value={tags}
              onChange={(ev) => setTags(ev.target.value)}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Add tags to help organize and find your work later
            </p>
          </div>

          {/* File Count */}
          {files.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
              </svg>
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={busy || files.length === 0}
            className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {busy ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Uploading...
              </span>
            ) : (
              'Upload to Portfolio'
            )}
          </button>
        </form>

        {/* Message */}
        {message && (
          <div
            className={`mt-6 rounded-lg border p-4 text-sm ${
              message.type === 'success'
                ? 'border-success/50 bg-success/10 text-success'
                : 'border-destructive/50 bg-destructive/10 text-destructive'
            }`}
          >
            <div className="flex items-center gap-2">
              {message.type === 'success' ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                </svg>
              )}
              {message.text}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

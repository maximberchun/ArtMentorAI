import { FormEvent, useState } from 'react'
import { apiFetch } from '../lib/api'
import { UploadResponse } from '../types/api'

export function PortfolioPage() {
  const [tags, setTags] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function upload(e: FormEvent) {
    e.preventDefault()
    if (files.length === 0) {
      setMessage('Select at least one image.')
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
      setMessage(`Uploaded ${data.ids.length} image(s).`)
      setFiles([])
      setTags('')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-4 rounded border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Portfolio upload</h2>
      <form className="space-y-3" onSubmit={upload}>
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          type="file"
          accept="image/*"
          multiple
          onChange={(ev) => setFiles(Array.from(ev.target.files ?? []))}
        />
        <input
          className="w-full rounded border border-stone-300 px-3 py-2 text-sm"
          placeholder="Tags (comma separated)"
          value={tags}
          onChange={(ev) => setTags(ev.target.value)}
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-stone-800 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          {busy ? 'Uploading...' : 'Upload to portfolio'}
        </button>
      </form>
      {files.length > 0 && (
        <p className="text-sm text-stone-600">{files.length} file(s) selected for upload.</p>
      )}
      {message && <p className="text-sm text-stone-700">{message}</p>}
    </section>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { listDocuments, deleteDocument } from '../api'

/**
 * DocumentList — shows all indexed documents from GET /api/documents.
 * Props:
 *   refreshTrigger: any value that changes to signal a re-fetch (e.g. upload count)
 */
export default function DocumentList({ refreshTrigger }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState(null)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listDocuments()
      setDocuments(data.documents || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments, refreshTrigger])

  async function handleDelete(doc) {
    if (!window.confirm(`Delete "${doc.document_name}"? This will remove all its indexed chunks from Qdrant.`)) return
    setDeletingId(doc.document_id)
    try {
      await deleteDocument(doc.document_id)
      setDocuments(prev => prev.filter(d => d.document_id !== doc.document_id))
    } catch (e) {
      alert(`Failed to delete: ${e.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  if (loading && documents.length === 0) {
    return (
      <div className="px-4 pb-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Indexed Documents
        </h3>
        <p className="text-xs text-gray-400 animate-pulse">Loading…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="px-4 pb-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Indexed Documents
        </h3>
        <p className="text-xs text-red-500">⚠️ {error}</p>
        <button onClick={fetchDocuments} className="text-xs text-blue-500 hover:underline mt-1">
          Retry
        </button>
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="px-4 pb-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Indexed Documents
        </h3>
        <p className="text-xs text-gray-400 italic text-center py-3">
          No documents indexed yet.
        </p>
      </div>
    )
  }

  return (
    <div className="px-4 pb-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center justify-between">
        <span>Indexed Documents</span>
        <button
          onClick={fetchDocuments}
          title="Refresh document list"
          className="text-gray-300 hover:text-gray-500 transition-colors"
        >
          ↻
        </button>
      </h3>
      <ul className="space-y-1.5">
        {documents.map(doc => (
          <li
            key={doc.document_id}
            className="flex items-start gap-2 text-xs text-gray-700 bg-green-50 border border-green-100 rounded-lg px-3 py-2 group"
          >
            <span className="mt-0.5 flex-shrink-0">📄</span>
            <div className="flex-1 min-w-0">
              <p className="truncate font-medium leading-snug" title={doc.document_name}>
                {doc.document_name}
              </p>
              <p className="text-gray-400 text-xs">
                {doc.chunks_count ?? doc.chunks_indexed ?? '?'} chunks · {doc.pages_count ?? '?'} pages
              </p>
            </div>
            <button
              onClick={() => handleDelete(doc)}
              disabled={deletingId === doc.document_id}
              title={`Delete "${doc.document_name}"`}
              className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-red-400 hover:text-red-600 disabled:opacity-30 ml-1"
            >
              {deletingId === doc.document_id ? '⏳' : '🗑️'}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

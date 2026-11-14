import { useState, useRef, useEffect, useCallback } from 'react'
import { uploadDocument, listDocuments, deleteDocument } from '../api'

export default function DocumentManager({ onDocumentsChanged }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listDocuments()
      setDocuments(data.documents || [])
      if (onDocumentsChanged) {
        onDocumentsChanged(data.documents || [])
      }
    } catch {
      // Backend may be offline during initial boot
    } finally {
      setLoading(false)
    }
  }, [onDocumentsChanged])

  useEffect(() => {
    fetchDocs()
  }, [fetchDocs])

  async function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus({
        type: 'error',
        message: 'Invalid file type. Only official PDF policy handbooks are accepted.'
      })
      return
    }

    setUploading(true)
    setUploadStatus(null)

    try {
      const res = await uploadDocument(file)
      setUploadStatus({
        type: 'success',
        message: `Indexed "${res.document_name}" (${res.chunks_indexed} clauses extracted)`
      })
      await fetchDocs()
    } catch (err) {
      setUploadStatus({
        type: 'error',
        message: err.message
      })
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  async function handleDelete(doc) {
    const confirmDelete = window.confirm(
      `Remove "${doc.document_name}" from active policy knowledge base? All indexed clauses and vector embeddings will be purged.`
    )
    if (!confirmDelete) return

    setDeletingId(doc.document_id)
    try {
      await deleteDocument(doc.document_id)
      await fetchDocs()
    } catch (err) {
      alert(`Deletion error: ${err.message}`)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-900 tracking-tight">Policy Knowledge Base</h2>
          <p className="text-xs text-slate-500">Official university documentation repository</p>
        </div>
        <button
          onClick={fetchDocs}
          title="Refresh indexed policy repository"
          className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
        >
          <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Upload Zone */}
      <div className="p-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-all duration-150 ${
            dragActive
              ? 'border-blue-500 bg-blue-50/50'
              : 'border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-slate-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFile(e.target.files[0])
              e.target.value = ''
            }}
          />
          <div className="flex flex-col items-center gap-1.5">
            <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-700">
                {uploading ? 'Processing & Chunking PDF...' : 'Upload policy handbook'}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">Drag PDF or browse files</p>
            </div>
          </div>
        </div>

        {/* Upload feedback */}
        {uploadStatus && (
          <div
            className={`mt-2.5 p-2.5 rounded-md text-xs leading-relaxed flex items-start gap-2 ${
              uploadStatus.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-rose-50 text-rose-800 border border-rose-200'
            }`}
          >
            <span className="flex-shrink-0 text-sm">
              {uploadStatus.type === 'success' ? '✓' : '⚠️'}
            </span>
            <span className="flex-1">{uploadStatus.message}</span>
            <button
              onClick={() => setUploadStatus(null)}
              className="text-slate-400 hover:text-slate-600 font-bold ml-1"
            >
              ×
            </button>
          </div>
        )}
      </div>

      {/* Active Documents List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Indexed Documents ({documents.length})
          </span>
          <span className="text-[11px] text-slate-400">Qdrant Active</span>
        </div>

        {documents.length === 0 ? (
          <div className="p-6 text-center border border-dashed border-slate-200 rounded-lg">
            <p className="text-xs text-slate-400">No documents indexed.</p>
            <p className="text-[11px] text-slate-400 mt-1">Upload a handbook above or verify sample policies are ingested.</p>
          </div>
        ) : (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.document_id}
                className="group p-2.5 rounded-lg border border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs transition-all flex items-start justify-between gap-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-slate-400">📄</span>
                    <p className="text-xs font-semibold text-slate-800 truncate" title={doc.document_name}>
                      {doc.document_name}
                    </p>
                    {/* Validity & Freshness Badge */}
                    {doc.validity_status === 'current' ? (
                      <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9px] font-semibold px-1.5 py-0.2 rounded">
                        Active ({doc.effective_academic_year || 'Current'})
                      </span>
                    ) : doc.validity_status === 'superseded' ? (
                      <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[9px] font-semibold px-1.5 py-0.2 rounded">
                        Superseded
                      </span>
                    ) : doc.validity_status === 'expired' ? (
                      <span className="bg-rose-50 text-rose-700 border border-rose-200 text-[9px] font-semibold px-1.5 py-0.2 rounded">
                        Expired
                      </span>
                    ) : (
                      <span className="bg-slate-100 text-slate-600 text-[9px] font-medium px-1.5 py-0.2 rounded">
                        v{doc.document_version || '1.0'}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                    <span>{doc.chunks_count ?? doc.chunks_indexed ?? '?'} clauses</span>
                    <span>•</span>
                    <span>{doc.pages_count ?? '?'} pages</span>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(doc)}
                  disabled={deletingId === doc.document_id}
                  title={`Delete ${doc.document_name}`}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-all flex-shrink-0"
                >
                  {deletingId === doc.document_id ? (
                    <span className="text-[10px] text-slate-400">...</span>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Grounding notice */}
      <div className="p-3 bg-slate-50 border-t border-slate-100 text-center">
        <p className="text-[11px] text-slate-500 leading-normal">
          Strictly grounded in uploaded university policies. Never generates unverified campus rules.
        </p>
      </div>
    </div>
  )
}

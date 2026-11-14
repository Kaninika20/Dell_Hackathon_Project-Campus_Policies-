import { useState, useRef } from 'react'
import { uploadDocument } from '../api'

export default function UploadPanel({ onUploaded }) {
  const [status, setStatus] = useState(null) // null | 'uploading' | 'done' | 'error'
  const [message, setMessage] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setStatus('error')
      setMessage('Please select a PDF file.')
      return
    }
    setStatus('uploading')
    setMessage(`Uploading "${file.name}"…`)
    try {
      const result = await uploadDocument(file)
      setStatus('done')
      setMessage(`✅ "${result.document_name}" — ${result.chunks_indexed} chunks indexed.`)
      onUploaded && onUploaded(result)
    } catch (e) {
      setStatus('error')
      setMessage(`❌ ${e.message}`)
    }
  }

  function onInputChange(e) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  const borderColor =
    dragOver ? 'border-blue-500 bg-blue-50' :
    status === 'done' ? 'border-green-400 bg-green-50' :
    status === 'error' ? 'border-red-400 bg-red-50' :
    'border-gray-300 bg-gray-50 hover:border-blue-400 hover:bg-blue-50'

  return (
    <div className="p-4">
      <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Upload Policy Document
      </h2>
      <div
        className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-colors ${borderColor}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={onInputChange} />
        <div className="text-2xl mb-1">📄</div>
        {status === 'uploading' ? (
          <p className="text-sm text-blue-600 font-medium animate-pulse">{message}</p>
        ) : message ? (
          <p className={`text-xs font-medium leading-snug ${status === 'done' ? 'text-green-700' : 'text-red-600'}`}>
            {message}
          </p>
        ) : (
          <>
            <p className="text-sm text-gray-600 font-medium">Drop PDF here</p>
            <p className="text-xs text-gray-400 mt-0.5">or click to browse</p>
          </>
        )}
      </div>
    </div>
  )
}

// API layer — Vite proxies /api → http://localhost:8000 and /health → http://localhost:8000

const BASE = ''

// ── Documents ────────────────────────────────────────────────────────────────

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  
  try {
    const res = await fetch(`${BASE}/api/documents/upload`, {
      method: 'POST',
      body: form,
    })
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `Upload failed with HTTP ${res.status}`)
    }
    return await res.json()
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Backend server is unreachable. Please ensure the API is running at http://localhost:8000.')
    }
    throw err
  }
}

export async function listDocuments() {
  try {
    const res = await fetch(`${BASE}/api/documents`)
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `Failed to fetch documents (${res.status})`)
    }
    return await res.json() // { documents: [...], total_count: n }
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Backend server is unreachable.')
    }
    throw err
  }
}

export async function deleteDocument(documentId) {
  try {
    const res = await fetch(`${BASE}/api/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `Delete failed with HTTP ${res.status}`)
    }
    return await res.json()
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Backend server is unreachable.')
    }
    throw err
  }
}

// ── Chat & Retrieval ──────────────────────────────────────────────────────────

/**
 * @param {string} question
 * @param {'baseline'|'hyde'|'hyde_hybrid'} retrievalMethod
 * @param {number} [topK=5]
 */
export async function askQuestion(question, retrievalMethod = 'hyde_hybrid', topK = 5) {
  try {
    const res = await fetch(`${BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        retrieval_method: retrievalMethod,
        top_k: topK,
      }),
    })
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `Chat request failed with HTTP ${res.status}`)
    }
    return await res.json()
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Cannot connect to CampusPolicy AI backend. Please verify the server is running.')
    }
    throw err
  }
}

// ── Health Check ──────────────────────────────────────────────────────────────

export async function getHealth() {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 4000)
    
    const res = await fetch(`${BASE}/health`, { signal: controller.signal })
    clearTimeout(timeoutId)
    
    if (!res.ok) throw new Error('Health check returned non-200')
    return await res.json()
  } catch (e) {
    return {
      status: 'offline',
      qdrant_ok: false,
      gemini_configured: false,
      error: e.message,
    }
  }
}


// ── Evaluation & Cache Telemetry ─────────────────────────────────────────────

export async function getEvaluationBenchmark(fresh = false) {
  const url = fresh ? `${BASE}/api/evaluation/benchmark?fresh=true` : `${BASE}/api/evaluation/benchmark`
  const res = await fetch(url)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Failed to fetch evaluation metrics')
  }
  return res.json()
}

export async function clearCache() {
  const res = await fetch(`${BASE}/api/evaluation/cache-clear`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to purge cache')
  return res.json()
}

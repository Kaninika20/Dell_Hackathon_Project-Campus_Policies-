import ReactMarkdown from 'react-markdown'

// ── Method badge ─────────────────────────────────────────────────────────────

const METHOD_LABELS = {
  baseline: { label: 'Baseline', color: 'bg-gray-100 text-gray-600' },
  hyde: { label: 'HyDE', color: 'bg-purple-100 text-purple-700' },
  hyde_hybrid: { label: 'HyDE + Hybrid', color: 'bg-blue-100 text-blue-700' },
}

function RetrievalBadge({ method, metadata }) {
  const info = METHOD_LABELS[method] || { label: method, color: 'bg-gray-100 text-gray-600' }
  const latency = metadata?.latency_ms != null ? `${Math.round(metadata.latency_ms)}ms` : null
  const chunks = metadata?.chunks_retrieved != null ? `${metadata.chunks_retrieved} chunks` : null

  return (
    <div className="flex flex-wrap gap-1.5 items-center mt-2">
      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${info.color}`}>
        {info.label}
      </span>
      {latency && (
        <span className="text-xs text-gray-400">⏱ {latency}</span>
      )}
      {chunks && (
        <span className="text-xs text-gray-400">· {chunks}</span>
      )}
    </div>
  )
}

// ── Source card ───────────────────────────────────────────────────────────────

function SourceCard({ source, index }) {
  // Support both old shape (source.document, source.page) and new Phase 2/3 shape
  const docName = source.document_name || source.document || 'Unknown document'
  const pageNum = source.page_number ?? source.page ?? '?'
  const heading = source.section_heading
  const excerpt = source.excerpt || source.text || ''

  return (
    <details className="text-xs border border-gray-200 rounded-lg overflow-hidden">
      <summary className="px-3 py-2 bg-gray-50 cursor-pointer hover:bg-gray-100 font-medium text-gray-700 flex gap-2 items-center select-none">
        <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 flex-shrink-0">
          #{index + 1}
        </span>
        <span className="truncate flex-1">{docName}</span>
        <span className="ml-auto text-gray-400 flex-shrink-0">p.{pageNum}</span>
      </summary>
      <div className="p-3 bg-white space-y-1">
        {heading && (
          <p className="text-gray-500 font-semibold">{heading}</p>
        )}
        {excerpt && (
          <p className="text-gray-600 leading-relaxed">{excerpt}</p>
        )}
      </div>
    </details>
  )
}

// ── Bubbles ───────────────────────────────────────────────────────────────────

export function UserBubble({ text }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-sm">
        {text}
      </div>
    </div>
  )
}

export function AssistantBubble({ answer, sources, retrieval_method, retrieval_metadata }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-2">
        {/* Answer bubble */}
        <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm shadow-sm">
          <div className="prose prose-sm max-w-none text-gray-800">
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
          {retrieval_method && (
            <RetrievalBadge method={retrieval_method} metadata={retrieval_metadata} />
          )}
        </div>

        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs text-gray-400 font-medium px-1">
              Sources ({sources.length})
            </p>
            {sources.map((s, i) => (
              <SourceCard key={i} source={s} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function LoadingBubble({ method }) {
  const info = METHOD_LABELS[method] || null
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center">
          {[0, 1, 2].map(i => (
            <span
              key={i}
              className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
          {info && (
            <span className={`ml-2 text-xs font-medium px-2 py-0.5 rounded-full ${info.color}`}>
              {info.label}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export function ErrorBubble({ text }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] bg-red-50 border border-red-200 text-red-700 rounded-2xl rounded-tl-sm px-4 py-3 text-sm shadow-sm">
        ⚠️ {text}
      </div>
    </div>
  )
}

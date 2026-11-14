import { useState } from 'react'

export const RETRIEVAL_MODES = [
  {
    id: 'baseline',
    label: 'Baseline Vector',
    shortLabel: 'Baseline',
    desc: 'Dense semantic similarity search using Gemini embeddings directly on query text.',
    badge: 'Standard Vector',
  },
  {
    id: 'hyde',
    label: 'HyDE Retrieval',
    shortLabel: 'HyDE',
    desc: 'Generates a hypothetical policy passage with formal terminology prior to dense vector search.',
    badge: 'Query Expansion',
  },
  {
    id: 'hyde_hybrid',
    label: 'HyDE + Hybrid (RRF)',
    shortLabel: 'HyDE + Hybrid',
    desc: 'Combines HyDE dense vector ranking with BM25 sparse keyword ranking using Reciprocal Rank Fusion.',
    badge: 'Recommended',
  },
]

export default function RetrievalSelector({ currentMode, onModeChange, latestMetadata }) {
  const [showDetails, setShowDetails] = useState(false)

  const activeMode = RETRIEVAL_MODES.find((m) => m.id === currentMode) || RETRIEVAL_MODES[2]

  return (
    <div className="bg-white border-b border-slate-200 px-4 py-2.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        {/* Mode Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1 hidden sm:inline">
            Retrieval Mode:
          </span>
          {RETRIEVAL_MODES.map((mode) => {
            const isSelected = currentMode === mode.id
            return (
              <button
                key={mode.id}
                onClick={() => onModeChange(mode.id)}
                className={`text-xs px-2.5 py-1.5 rounded-md font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                }`}
              >
                <span>{mode.shortLabel}</span>
                {mode.id === 'hyde_hybrid' && (
                  <span className={`text-[10px] px-1 py-0.2 rounded ${isSelected ? 'bg-blue-500 text-white' : 'bg-slate-200 text-slate-600'}`}>
                    ★
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* Telemetry / Inspector Toggle */}
        <div className="flex items-center gap-2">
          {latestMetadata && (
            <div className="flex items-center gap-2 text-[11px] text-slate-500 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-md">
              <span className="font-mono text-slate-700">⏱ {Math.round(latestMetadata.latency_ms)}ms</span>
              {latestMetadata.cached && (
                <>
                  <span>•</span>
                  <span className="text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                    ⚡ {latestMetadata.cache_type === 'semantic' ? `Semantic (${Math.round((latestMetadata.similarity_score || 0.9) * 100)}%)` : 'Exact'}
                  </span>
                </>
              )}
              <span>•</span>
              <span>{latestMetadata.chunks_retrieved} chunks</span>
              {latestMetadata.query_injection_detected && (
                <span className="text-amber-600 font-semibold bg-amber-50 px-1 rounded">Sanitized</span>
              )}
            </div>
          )}
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-[11px] text-slate-400 hover:text-slate-700 underline flex items-center gap-0.5"
          >
            <span>{showDetails ? 'Hide' : 'Info'}</span>
          </button>
        </div>
      </div>

      {/* Expanded details banner */}
      {showDetails && (
        <div className="mt-2.5 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
          <div className="flex items-start justify-between">
            <div>
              <span className="font-semibold text-slate-800">{activeMode.label}</span>
              <p className="text-slate-500 mt-0.5">{activeMode.desc}</p>
            </div>
            <span className="text-[10px] font-mono bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-semibold">
              {activeMode.badge}
            </span>
          </div>

          {latestMetadata?.hypothetical_passage && (
            <div className="pt-2 border-t border-slate-200">
              <span className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider block mb-1">
                Generated HyDE Passage (Retrieval Artifact Only):
              </span>
              <p className="text-[11px] italic text-slate-600 bg-white p-2 rounded border border-slate-200">
                "{latestMetadata.hypothetical_passage}"
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

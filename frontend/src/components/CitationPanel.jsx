import { useState } from 'react'

export default function CitationPanel({ sources }) {
  const [openIndex, setOpenIndex] = useState(0)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3 pt-3 border-t border-slate-100">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Policy Citations ({sources.length})
        </span>
        <span className="text-[10px] text-slate-400">Click citation to inspect text</span>
      </div>

      <div className="space-y-1.5">
        {sources.map((src, i) => {
          const isOpen = openIndex === i
          const docName = src.document_name || src.document || 'Handbook'
          const page = src.page_number ?? src.page ?? '?'
          const heading = src.section_heading || 'Policy Clause'
          const excerpt = src.excerpt || src.text || ''

          return (
            <div
              key={i}
              className={`rounded-md border transition-all text-xs overflow-hidden ${
                isOpen ? 'border-blue-200 bg-blue-50/20' : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <button
                type="button"
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full px-3 py-2 flex items-center justify-between gap-2 text-left select-none"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-600 font-mono text-[10px] flex items-center justify-center flex-shrink-0">
                    {i + 1}
                  </span>
                  <span className="font-semibold text-slate-800 truncate" title={docName}>
                    {docName}
                  </span>
                  <span className="text-slate-400 text-[11px] truncate hidden sm:inline">
                    — {heading}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="font-mono text-[11px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                    p. {page}
                  </span>
                  <svg
                    className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {isOpen && (
                <div className="px-3 pb-3 pt-1 border-t border-slate-100 text-slate-700 bg-white">
                  <p className="font-medium text-slate-900 text-[11px] mb-1">
                    Section: {heading}
                  </p>
                  <p className="text-[11px] leading-relaxed text-slate-600 font-serif bg-slate-50 p-2 rounded border border-slate-100">
                    "{excerpt}"
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}


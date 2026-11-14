import { useState, useEffect } from 'react'
import { getHealth } from '../api'

export default function StatusBar() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    let mounted = true
    async function check() {
      const res = await getHealth()
      if (mounted) setHealth(res)
    }
    check()
    const timer = setInterval(check, 25000)
    return () => {
      mounted = false
      clearInterval(timer)
    }
  }, [])

  if (!health) return null

  const isOnline = health.status === 'ok'
  const isQdrantOk = health.qdrant_ok
  const isGeminiOk = health.gemini_configured

  return (
    <div className="bg-slate-900 text-slate-300 text-[11px] px-4 py-1.5 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800">
      <div className="flex items-center gap-4">
        {/* Backend API status */}
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-rose-500 animate-pulse'}`} />
          <span className="text-slate-400">FastAPI:</span>
          <span className={isOnline ? 'text-slate-200 font-medium' : 'text-rose-400 font-medium'}>
            {isOnline ? 'Connected' : 'Offline'}
          </span>
        </div>

        {/* Qdrant Status */}
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${isQdrantOk ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="text-slate-400">Qdrant Cloud:</span>
          <span className={isQdrantOk ? 'text-slate-200 font-medium' : 'text-amber-400 font-medium'}>
            {isQdrantOk ? 'Active' : 'Unreachable'}
          </span>
        </div>

        {/* Gemini Status */}
        <div className="flex items-center gap-1.5 hidden sm:flex">
          <span className={`w-1.5 h-1.5 rounded-full ${isGeminiOk ? 'bg-emerald-400' : 'bg-rose-500'}`} />
          <span className="text-slate-400">Gemini API:</span>
          <span className={isGeminiOk ? 'text-slate-200 font-medium' : 'text-rose-400 font-medium'}>
            {isGeminiOk ? 'Configured' : 'Missing Key'}
          </span>
        </div>

        {/* Semantic Cache Status */}
        <div className="flex items-center gap-1.5 hidden md:flex">
          <span className={`w-1.5 h-1.5 rounded-full ${health.cache_enabled ? 'bg-emerald-400' : 'bg-slate-500'}`} />
          <span className="text-slate-400">Semantic Cache:</span>
          <span className="text-slate-200 font-medium">
            {health.redis_available ? 'Redis' : health.cache_enabled ? 'In-Memory' : 'Disabled'}
          </span>
        </div>
      </div>

      <div className="text-slate-400 text-[11px] font-mono hidden md:block">
        CampusPolicy AI v1.0.0
      </div>
    </div>
  )
}

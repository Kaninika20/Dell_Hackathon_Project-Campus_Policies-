import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../api'
import { UserBubble, AssistantBubble, LoadingBubble, ErrorBubble } from './ChatBubbles'

const SUGGESTIONS = [
  'What is the academic integrity policy?',
  'How many absences are allowed per semester?',
  'What are the consequences of plagiarism?',
  'Can I get attendance relaxation due to medical reasons?',
]

const RETRIEVAL_MODES = [
  {
    value: 'baseline',
    label: 'Baseline',
    description: 'Direct semantic search',
    icon: '🔍',
    color: 'border-gray-300 text-gray-700 bg-white hover:border-gray-400',
    activeColor: 'border-gray-500 bg-gray-100 text-gray-900 font-semibold',
  },
  {
    value: 'hyde',
    label: 'HyDE',
    description: 'Hypothetical document expansion',
    icon: '🧠',
    color: 'border-purple-200 text-purple-700 bg-white hover:border-purple-400',
    activeColor: 'border-purple-500 bg-purple-50 text-purple-900 font-semibold',
  },
  {
    value: 'hyde_hybrid',
    label: 'HyDE + Hybrid',
    description: 'HyDE + BM25 keyword fusion',
    icon: '⚡',
    color: 'border-blue-200 text-blue-700 bg-white hover:border-blue-400',
    activeColor: 'border-blue-500 bg-blue-50 text-blue-900 font-semibold',
  },
]

export default function ChatPanel() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [retrievalMethod, setRetrievalMethod] = useState('hyde_hybrid')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendQuestion(question) {
    if (!question.trim() || loading) return
    const q = question.trim()
    setInput('')
    setMessages(prev => [...prev, { type: 'user', text: q }])
    setLoading(true)
    try {
      const result = await askQuestion(q, retrievalMethod)
      setMessages(prev => [
        ...prev,
        {
          type: 'assistant',
          answer: result.answer,
          sources: result.sources,
          retrieval_method: result.retrieval_method,
          retrieval_metadata: result.retrieval_metadata,
        },
      ])
    } catch (e) {
      setMessages(prev => [...prev, { type: 'error', text: e.message }])
    } finally {
      setLoading(false)
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendQuestion(input)
    }
  }

  const activeMode = RETRIEVAL_MODES.find(m => m.value === retrievalMethod)

  return (
    <div className="flex flex-col h-full">

      {/* Retrieval mode selector */}
      <div className="border-b border-gray-100 px-4 py-2 bg-gray-50">
        <p className="text-xs text-gray-400 mb-1.5 font-medium">Retrieval mode</p>
        <div className="flex gap-2 flex-wrap">
          {RETRIEVAL_MODES.map(mode => (
            <button
              key={mode.value}
              onClick={() => setRetrievalMethod(mode.value)}
              title={mode.description}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all flex items-center gap-1.5 ${
                retrievalMethod === mode.value ? mode.activeColor : mode.color
              }`}
            >
              <span>{mode.icon}</span>
              <span>{mode.label}</span>
            </button>
          ))}
        </div>
        {activeMode && (
          <p className="text-xs text-gray-400 mt-1">{activeMode.icon} {activeMode.description}</p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 py-12">
            <div className="text-5xl">🏛️</div>
            <h2 className="text-xl font-semibold text-gray-700">CampusPolicy AI</h2>
            <p className="text-gray-500 text-sm max-w-sm">
              Ask any question about your university's policies.
              Upload a PDF document from the sidebar to get started.
            </p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-4">
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => sendQuestion(s)}
                  disabled={loading}
                  className="text-left text-sm px-4 py-2 bg-white border border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50 text-gray-600 transition-colors disabled:opacity-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.type === 'user') return <UserBubble key={i} text={msg.text} />
          if (msg.type === 'assistant')
            return (
              <AssistantBubble
                key={i}
                answer={msg.answer}
                sources={msg.sources}
                retrieval_method={msg.retrieval_method}
                retrieval_metadata={msg.retrieval_metadata}
              />
            )
          if (msg.type === 'error') return <ErrorBubble key={i} text={msg.text} />
          return null
        })}

        {loading && <LoadingBubble method={retrievalMethod} />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask about a university policy…"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-h-32 overflow-y-auto"
            style={{ minHeight: '48px' }}
          />
          <button
            onClick={() => sendQuestion(input)}
            disabled={!input.trim() || loading}
            className="px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors font-medium text-sm flex-shrink-0"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}

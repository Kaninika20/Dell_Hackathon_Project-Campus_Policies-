import { useState } from 'react'
import StatusBar from './components/StatusBar'
import DocumentManager from './components/DocumentManager'
import ChatDashboard from './components/ChatDashboard'
import RetrievalSelector from './components/RetrievalSelector'
import EvaluationDashboard from './components/EvaluationDashboard'

export default function App() {
  const [retrievalMode, setRetrievalMode] = useState('hyde_hybrid')
  const [latestMetadata, setLatestMetadata] = useState(null)
  const [activeTab, setActiveTab] = useState('chat') // Mobile: 'chat' | 'documents'
  const [currentView, setCurrentView] = useState('chat') // Desktop view: 'chat' | 'evaluation'

  return (
    <div className="h-screen flex flex-col bg-slate-100 font-sans text-slate-900 overflow-hidden">
      {/* Top Banner / System Telemetry */}
      <StatusBar />

      {/* Primary University Navigation Header */}
      <header className="bg-white border-b border-slate-200 px-4 sm:px-6 py-2.5 flex items-center justify-between flex-shrink-0 shadow-2xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 text-white font-serif font-black flex items-center justify-center text-sm shadow-xs">
            CP
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold text-slate-900 leading-tight tracking-tight">
                CampusPolicy AI
              </h1>
              <span className="bg-blue-50 text-blue-700 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-blue-100">
                Official Assistant
              </span>
            </div>
            <p className="text-[11px] text-slate-500 hidden sm:block">
              AI-Powered University Regulations & Policy Discovery Assistant
            </p>
          </div>
        </div>

        {/* View Switcher (Chat vs Evaluation Dashboard) */}
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex border border-slate-200 rounded-lg p-0.5 bg-slate-50 text-xs">
            <button
              onClick={() => setCurrentView('chat')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                currentView === 'chat' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>💬</span>
              <span>Policy Assistant</span>
            </button>
            <button
              onClick={() => setCurrentView('evaluation')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                currentView === 'evaluation' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>📊</span>
              <span>Retrieval Evaluation</span>
            </button>
          </div>

          {/* Mobile View Toggle */}
          <div className="flex md:hidden border border-slate-200 rounded-lg p-0.5 bg-slate-50 text-xs">
            <button
              onClick={() => { setActiveTab('chat'); setCurrentView('chat') }}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                activeTab === 'chat' && currentView === 'chat' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                activeTab === 'documents' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600'
              }`}
            >
              Docs
            </button>
            <button
              onClick={() => setCurrentView('evaluation')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                currentView === 'evaluation' ? 'bg-white text-blue-600 shadow-xs' : 'text-slate-600'
              }`}
            >
              Eval
            </button>
          </div>
        </div>
      </header>

      {/* Main Responsive Grid Layout */}
      {currentView === 'evaluation' ? (
        <div className="flex-1 overflow-hidden flex flex-col">
          <EvaluationDashboard />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
          {/* Left Sidebar — Document Repository (Visible on desktop or when 'documents' selected on mobile) */}
          <aside
            className={`w-full md:w-80 lg:w-96 flex-shrink-0 h-full ${
              activeTab === 'documents' ? 'flex flex-col' : 'hidden md:flex md:flex-col'
            }`}
          >
            <DocumentManager />
          </aside>

          {/* Right Section — Retrieval Selector & Conversational Workspace */}
          <main
            className={`flex-1 flex flex-col h-full min-w-0 ${
              activeTab === 'chat' ? 'flex' : 'hidden md:flex'
            }`}
          >
            {/* Retrieval Comparison Switcher */}
            <RetrievalSelector
              currentMode={retrievalMode}
              onModeChange={setRetrievalMode}
              latestMetadata={latestMetadata}
            />

            {/* Chat Dashboard */}
            <div className="flex-1 overflow-hidden">
              <ChatDashboard
                currentMode={retrievalMode}
                onMetadataReceived={setLatestMetadata}
              />
            </div>
          </main>
        </div>
      )}
    </div>
  )
}

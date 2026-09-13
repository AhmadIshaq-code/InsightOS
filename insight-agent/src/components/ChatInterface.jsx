import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../hooks/useChat';
import { useFileUpload } from '../hooks/useFileUpload';
import MessageBubble from './MessageBubble';
import { 
  Sparkles, 
  Send, 
  Trash2, 
  Database, 
  FileText, 
  TrendingUp, 
  ShieldAlert, 
  Search, 
  ArrowRight,
  Layers,
  ChevronDown,
  RotateCcw,
  Zap
} from 'lucide-react';

const SUGGESTED_PROMPTS = [
  {
    title: "Analyze my revenue",
    query: "What is the total revenue and how is it distributed across products?",
    icon: Database,
    accent: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20"
  },
  {
    title: "Find unusual values",
    query: "Find revenue anomalies and unusual outliers in the dataset.",
    icon: ShieldAlert,
    accent: "text-amber-400 bg-amber-500/10 border-amber-500/20"
  },
  {
    title: "Forecast revenue",
    query: "Forecast the next 3 months of revenue based on historical trends.",
    icon: TrendingUp,
    accent: "text-purple-400 bg-purple-500/10 border-purple-500/20"
  },
  {
    title: "Search uploaded policies",
    query: "What does the IT security policy say about passwords and incident reporting?",
    icon: FileText,
    accent: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
  },
  {
    title: "Hybrid synthesis",
    query: "Compare revenue performance with the employee handbook and SOP policy.",
    icon: Zap,
    accent: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
  }
];

const ChatInterface = () => {
  const { 
    messages, 
    isLoading, 
    sendMessage, 
    clearChat, 
    retryLastMessage,
    selectedDatasetId, 
    setSelectedDatasetId, 
    datasets 
  } = useChat();
  const { isProcessing } = useFileUpload();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || isProcessing) return;

    const userMessage = input.trim();
    setInput('');
    await sendMessage(userMessage);
  };

  const handlePromptClick = async (promptQuery) => {
    if (isLoading || isProcessing) return;
    await sendMessage(promptQuery);
  };

  const handleClearChat = () => {
    if (messages.length === 0) return;
    if (window.confirm('Clear current chat conversation?')) {
      clearChat();
    }
  };

  const activeDataset = datasets.find(d => d.dataset_id === selectedDatasetId);

  return (
    <div className="flex flex-col h-full bg-[#070709] relative">
      {/* Top Context & Dataset Bar */}
      <div className="px-4 py-2.5 md:px-8 border-b border-white/5 bg-black/40 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-slate-400 font-medium">Active Context:</span>
          
          {datasets.length > 0 ? (
            <div className="relative inline-block">
              <select
                value={selectedDatasetId || ''}
                onChange={(e) => setSelectedDatasetId(e.target.value || null)}
                className="bg-slate-900/90 text-indigo-300 font-semibold text-xs py-1 px-2.5 pr-7 rounded-lg border border-indigo-500/30 outline-none hover:border-indigo-500/50 cursor-pointer appearance-none"
              >
                <option value="">Auto-detect (Latest Dataset)</option>
                {datasets.map((d) => (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    📊 {d.filename || d.dataset_id.slice(0, 10)} ({d.row_count || 'active'} rows)
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-indigo-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          ) : (
            <span className="text-slate-500 italic">No structured datasets uploaded yet</span>
          )}
        </div>

        {messages.length > 0 && (
          <button
            type="button"
            onClick={handleClearChat}
            className="flex items-center gap-1.5 text-slate-400 hover:text-rose-400 transition-colors cursor-pointer text-xs font-semibold py-1 px-2 rounded-lg hover:bg-white/5"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 sm:p-6 md:p-10 space-y-6">
        {messages.length === 0 ? (
          /* Empty State */
          <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center px-4 py-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-2xl shadow-indigo-500/30 mb-5 border border-indigo-400/30">
              <Sparkles className="w-7 h-7" />
            </div>

            <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight mb-2">
              InsightOS AI Analyst
            </h2>
            <p className="text-slate-400 text-sm md:text-base max-w-lg mb-8 leading-relaxed">
              Ask deterministic questions about your structured datasets, retrieve verified PDF policies, or synthesize both without hallucinations.
            </p>

            {/* Quick Prompts Grid */}
            <div className="w-full text-left space-y-2.5">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 px-1">
                Suggested Questions
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {SUGGESTED_PROMPTS.map((p, idx) => {
                  const Icon = p.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handlePromptClick(p.query)}
                      className={`flex items-start gap-3 p-3.5 rounded-2xl border text-left transition-all duration-200 hover:scale-[1.01] cursor-pointer ${p.accent} hover:bg-white/5`}
                    >
                      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold text-xs text-slate-200">{p.title}</div>
                        <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{p.query}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble 
              key={msg.id} 
              message={msg} 
              onRetry={(failedPrompt) => sendMessage(failedPrompt || input)}
            />
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex gap-3 justify-start items-start w-full">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-1 shadow-lg">
              <Sparkles className="w-4 h-4 animate-pulse" />
            </div>
            <div className="glass-card border border-indigo-500/30 rounded-3xl rounded-tl-none p-5 text-sm text-slate-300 shadow-2xl flex items-center gap-3">
              <div className="flex space-x-1.5">
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs font-medium text-slate-400">
                Reasoning across Data Brain & Knowledge Brain...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form Area */}
      <div className="p-4 sm:p-6 md:p-8 border-t border-white/5 bg-black/60 backdrop-blur-xl">
        <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
          <div className="relative glass-card rounded-2xl border border-white/10 overflow-hidden shadow-2xl focus-within:border-indigo-500/50 transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder={
                isProcessing 
                  ? "Ingesting data assets..." 
                  : "Ask a business question, forecast metrics, search policies..."
              }
              rows={2}
              className="w-full bg-transparent p-4 text-sm md:text-base text-slate-100 placeholder-slate-500 outline-none resize-none leading-relaxed"
              disabled={isLoading || isProcessing}
            />

            <div className="flex items-center justify-between px-4 pb-3 pt-1 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <span className="hidden sm:inline">Press</span>
                <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] font-mono text-slate-400">Enter</kbd>
                <span className="hidden sm:inline">to send,</span>
                <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] font-mono text-slate-400">Shift+Enter</kbd>
                <span className="hidden sm:inline">for newline</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={isLoading || isProcessing || !input.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white rounded-xl font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-lg shadow-indigo-600/20 active:scale-95"
                >
                  {isLoading ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span className="text-xs">Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <span className="text-xs">Send</span>
                      <Send className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;


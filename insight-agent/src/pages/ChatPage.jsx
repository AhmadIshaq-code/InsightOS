import React from 'react';
import ChatInterface from '../components/ChatInterface';
import { Sparkles, ShieldCheck, Activity } from 'lucide-react';

const ChatPage = () => {
  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#050505]">
      {/* Header */}
      <header className="px-6 py-4 border-b border-white/5 glass-card shrink-0 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg md:text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              AI Analyst
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Grounded & Safe
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Data Brain Analytics • PDF Knowledge Retrieval • Hybrid Reasoning
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>Zero Code Exec Safe</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300 font-medium">Core API Connected</span>
          </div>
        </div>
      </header>

      {/* Main Chat Interface */}
      <main className="flex-1 overflow-hidden relative">
        <ChatInterface />
      </main>
    </div>
  );
};

export default ChatPage;


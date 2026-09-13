import React, { useContext, useState } from 'react';
import { APIContext } from '../context/APIContext';
import { Settings, Check } from 'lucide-react';

const SettingsPage = () => {
  const { apiKey, updateApiKey } = useContext(APIContext);
  const [tempKey, setTempKey] = useState(apiKey);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    updateApiKey(tempKey);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex-1 p-8 md:p-12 overflow-y-auto custom-scrollbar">
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
            <Settings className="w-8 h-8 text-indigo-500" />
            Configuration
          </h1>
          <p className="text-slate-400">Manage your API keys and data sources.</p>
        </div>

        <div className="glass-card rounded-3xl p-8 space-y-6">
          
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-2">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm">🔑</span>
                Groq API Key (Optional)
              </h3>
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative text-xs text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 px-3 py-1.5 rounded-lg font-medium transition-all border border-indigo-500/20 flex items-center gap-1 hover:border-indigo-500/40"
              >
                Get Free API Key
                <div className="absolute opacity-0 group-hover:opacity-100 bg-slate-800 text-slate-200 border border-white/10 text-xs px-2 py-1 rounded-md shadow-lg -bottom-8 right-0 whitespace-nowrap transition-opacity pointer-events-none z-10">
                  How to get Groq Free API
                </div>
              </a>
            </div>
            <div className="flex gap-4">
              <input
                type="password"
                value={tempKey}
                onChange={(e) => setTempKey(e.target.value)}
                placeholder="Uses backend .env by default..."
                className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                onClick={handleSave}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 min-w-[120px] justify-center"
              >
                {saved ? <Check className="w-5 h-5" /> : 'Save Key'}
              </button>
            </div>
            <p className="text-sm text-slate-500 mt-2">Leave this blank to use the default API key configured in the Python backend.</p>
          </div>

          <div className="h-px w-full bg-white/5" />

          <div>
            <h3 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <span className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-sm">⚡</span>
              Platform Architecture & Status
            </h3>
            <div className="bg-black/30 border border-white/5 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Core Engine</span>
                <span className="text-white font-medium">InsightOS Hybrid RAG & Analytics</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">LLM Provider</span>
                <span className="text-emerald-400 font-medium">Groq (LLaMA 3.3 70B Versatile)</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Embeddings</span>
                <span className="text-white font-medium">HuggingFace all-MiniLM-L6-v2</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Vector Store</span>
                <span className="text-white font-medium">Chroma DB (Local Persistent)</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default SettingsPage;

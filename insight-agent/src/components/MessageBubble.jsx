import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  LineChart, 
  Line 
} from 'recharts';
import { 
  Bot, 
  User, 
  AlertCircle, 
  RefreshCw, 
  Sparkles, 
  Database, 
  FileText,
  Clock
} from 'lucide-react';
import StructuredResponse from './StructuredResponse';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

const renderChart = (chartConfig) => {
  if (!chartConfig || !chartConfig.data || chartConfig.data.length === 0) return null;

  const { type, title, data, x_key, y_key } = chartConfig;

  return (
    <div className="mt-4 w-full h-80 bg-slate-950/60 p-4 rounded-2xl border border-slate-800 shadow-xl">
      {title && <h3 className="text-center text-slate-200 font-semibold mb-4 text-xs md:text-sm">{title}</h3>}
      <ResponsiveContainer width="100%" height="100%">
        {type === 'bar' && (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={x_key} stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#475569', borderRadius: '0.75rem' }} />
            <Legend />
            <Bar dataKey={y_key} fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
        {type === 'pie' && (
          <PieChart>
            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#475569', borderRadius: '0.75rem' }} />
            <Legend />
            <Pie data={data} dataKey={y_key} nameKey={x_key} cx="50%" cy="50%" outerRadius={90} fill="#8884d8" label>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        )}
        {type === 'line' && (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={x_key} stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#475569', borderRadius: '0.75rem' }} />
            <Legend />
            <Line type="monotone" dataKey={y_key} stroke="#818cf8" strokeWidth={2.5} dot={{ r: 4 }} />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
};

const MessageBubble = ({ message, onRetry }) => {
  const isUser = message.role === 'user';
  const isError = message.role === 'error';

  let textContent = "";
  let chartConfig = null;
  let rawResponse = message.rawResponse || null;
  
  if (typeof message.content === 'string') {
    textContent = message.content;
  } else if (message.content && typeof message.content === 'object') {
    textContent = message.content.answer || "";
    chartConfig = message.content.chart || null;
    if (!rawResponse) rawResponse = message.content;
  }

  const timeString = message.timestamp 
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  // Get intent badge label
  const intent = rawResponse?.intent || '';
  const badgeLabel = intent === 'HYBRID' 
    ? 'Hybrid Analyst' 
    : (intent === 'DATA' ? 'Data Brain' : (intent === 'DOCS' ? 'Knowledge Brain' : 'AI Analyst'));

  return (
    <div className={`flex gap-3 w-full ${isUser ? 'justify-end' : 'justify-start'} group`}>
      {/* Assistant Icon */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-1 shadow-lg backdrop-blur-md">
          {isError ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : (
            <Sparkles className="w-4 h-4 text-indigo-400" />
          )}
        </div>
      )}

      {/* Bubble Container */}
      <div 
        className={`max-w-3xl w-full rounded-3xl p-5 md:p-6 transition-all duration-200 ${
          isUser 
            ? 'bg-indigo-600/15 border border-indigo-500/30 rounded-tr-none text-slate-100' 
            : isError 
              ? 'bg-rose-950/20 border border-rose-500/40 rounded-tl-none text-rose-200' 
              : 'glass-card border border-white/10 rounded-tl-none text-slate-200 shadow-2xl'
        }`}
      >
        {/* Header inside Bubble */}
        <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-white/5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-300">
              {isUser ? 'You' : badgeLabel}
            </span>
            {!isUser && !isError && intent && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase tracking-wider bg-white/5 border border-white/10 text-indigo-300">
                {intent}
              </span>
            )}
            {rawResponse?.confidence && (
              <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                ({Math.round(rawResponse.confidence * 100)}% grounded)
              </span>
            )}
          </div>
          {timeString && (
            <span className="text-[11px] text-slate-500 flex items-center gap-1 font-mono">
              <Clock className="w-3 h-3" />
              {timeString}
            </span>
          )}
        </div>

        {/* Bubble Content */}
        {isUser ? (
          <div className="text-sm md:text-base leading-relaxed whitespace-pre-wrap text-slate-100">
            {textContent}
          </div>
        ) : isError ? (
          <div className="space-y-3">
            <div className="flex items-start gap-2.5 text-rose-300 text-sm">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-semibold block mb-0.5">Analyst Request Failed</span>
                <span className="text-slate-300 text-xs">{textContent}</span>
              </div>
            </div>

            {onRetry && (
              <button
                type="button"
                onClick={() => onRetry(message.failedPrompt)}
                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold transition-all cursor-pointer shadow-sm active:scale-95"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retry Question</span>
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <StructuredResponse rawResponse={rawResponse} textContent={textContent} />
            {chartConfig && renderChart(chartConfig)}
          </div>
        )}
      </div>

      {/* User Icon */}
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-1 shadow-lg">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};

export default MessageBubble;

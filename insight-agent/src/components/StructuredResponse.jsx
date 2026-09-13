import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Database, 
  FileText, 
  Sparkles, 
  TrendingUp, 
  TrendingDown, 
  AlertTriangle, 
  ExternalLink, 
  ShieldAlert, 
  Calendar,
  Layers,
  CheckCircle2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

/**
 * Parses markdown text into distinct InsightOS structured sections if present.
 */
function parseStructuredSections(text) {
  if (!text || typeof text !== 'string') return null;

  const hasHybridHeaders = 
    text.includes('DATA FINDINGS') || 
    text.includes('DOCUMENT EVIDENCE') || 
    text.includes('AI INTERPRETATION') ||
    text.includes('CITATIONS');

  if (!hasHybridHeaders) return null;

  // Regex splitting on section headers
  const sections = {
    header: '',
    dataFindings: '',
    docEvidence: '',
    interpretation: '',
    citations: '',
    isForecast: false,
    isAnomaly: false
  };

  // Check special flags
  sections.isForecast = text.includes('DATA FINDINGS (FORECAST)') || text.toLowerCase().includes('time-series forecast') || text.toLowerCase().includes('projected estimates');
  sections.isAnomaly = text.includes('Statistical Anomaly Detection') || text.includes('Identified Outliers') || text.includes('IQR Method');

  // Match standard sections
  const dataMatch = text.match(/(?:###\s*📊\s*DATA FINDINGS.*?\n|📊\s*\*\*DATA FINDINGS.*?\*\*\n)([\s\S]*?)(?=(?:###\s*📄\s*DOCUMENT EVIDENCE|###\s*⚡\s*AI INTERPRETATION|###\s*🔗\s*CITATIONS|\*\*Sources:\*\*|$))/i);
  if (dataMatch) sections.dataFindings = dataMatch[1].trim();

  const docMatch = text.match(/(?:###\s*📄\s*DOCUMENT EVIDENCE.*?\n)([\s\S]*?)(?=(?:###\s*⚡\s*AI INTERPRETATION|###\s*🔗\s*CITATIONS|\*\*Sources:\*\*|$))/i);
  if (docMatch) sections.docEvidence = docMatch[1].trim();

  const interpMatch = text.match(/(?:###\s*⚡\s*AI INTERPRETATION.*?\n)([\s\S]*?)(?=(?:###\s*🔗\s*CITATIONS|\*\*Sources:\*\*|$))/i);
  if (interpMatch) sections.interpretation = interpMatch[1].trim();

  const citeMatch = text.match(/(?:###\s*🔗\s*CITATIONS.*?\n|\*\*Sources:\*\*\n)([\s\S]*?)$/i);
  if (citeMatch) sections.citations = citeMatch[1].trim();

  // If none matched cleanly, fallback
  if (!sections.dataFindings && !sections.docEvidence && !sections.interpretation && !sections.citations) {
    return null;
  }

  return sections;
}

/**
 * Highlight forecast values and disclaimers to ensure predictions are never confused with historical facts.
 */
const ForecastBanner = () => (
  <div className="mb-4 p-3.5 rounded-xl bg-purple-950/40 border border-purple-500/30 flex items-start gap-3 text-xs text-purple-200 shadow-lg backdrop-blur-sm">
    <TrendingUp className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
    <div>
      <div className="font-semibold text-purple-300 flex items-center gap-2">
        <span>PROJECTED ESTIMATES (FORECAST)</span>
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
          Model Projection
        </span>
      </div>
      <p className="mt-1 text-slate-400 leading-relaxed">
        Future values are statistical extrapolations based on historical patterns. They are mathematical projections, not historical facts.
      </p>
    </div>
  </div>
);

/**
 * Highlight statistical anomalies and outliers clearly with metric, value, and context.
 */
const AnomalyBanner = () => (
  <div className="mb-4 p-3.5 rounded-xl bg-amber-950/30 border border-amber-500/30 flex items-start gap-3 text-xs text-amber-200 shadow-lg backdrop-blur-sm">
    <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
    <div>
      <div className="font-semibold text-amber-300 flex items-center gap-2">
        <span>STATISTICAL ANOMALIES DETECTED</span>
        <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
          IQR Method
        </span>
      </div>
      <p className="mt-1 text-slate-400 leading-relaxed">
        Values outside normal distribution boundaries have been isolated deterministically.
      </p>
    </div>
  </div>
);

const StructuredResponse = ({ rawResponse, textContent }) => {
  const [docPassagesOpen, setDocPassagesOpen] = useState(true);

  const parsed = parseStructuredSections(textContent);

  // If no structured section headers are found, detect if single-intent DATA or DOCS with forecast/anomaly
  const isForecast = rawResponse?.answer?.includes('FORECAST') || textContent?.includes('FORECAST') || textContent?.includes('Projected Estimates');
  const isAnomaly = rawResponse?.answer?.includes('Statistical Anomaly Detection') || textContent?.includes('Statistical Anomaly Detection');

  // Grounded document evidence chunks from response object if available
  const docChunks = Array.isArray(rawResponse?.document_evidence) ? rawResponse.document_evidence : [];
  const citationsList = Array.isArray(rawResponse?.citations) ? rawResponse.citations : [];
  const dataFactsList = Array.isArray(rawResponse?.data_facts) ? rawResponse.data_facts : [];

  // Fallback to standard Markdown if it's a simple unformatted string or general chat
  if (!parsed && !isForecast && !isAnomaly && docChunks.length === 0 && citationsList.length === 0) {
    return (
      <div className="prose prose-sm prose-invert max-w-none text-slate-300 leading-relaxed">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
      </div>
    );
  }

  return (
    <div className="space-y-4 w-full text-slate-200 text-sm">
      {/* Forecast Special Banner */}
      {isForecast && <ForecastBanner />}

      {/* Anomaly Special Banner */}
      {isAnomaly && <AnomalyBanner />}

      {/* 1. DATA FINDINGS SECTION */}
      {(parsed?.dataFindings || dataFactsList.length > 0) && (
        <div className="rounded-2xl bg-gradient-to-b from-indigo-950/40 to-slate-900/60 border border-indigo-500/30 p-4 shadow-xl backdrop-blur-md">
          <div className="flex items-center gap-2 pb-2.5 mb-3 border-b border-indigo-500/20 text-indigo-400 font-semibold text-xs tracking-wider uppercase">
            <Database className="w-4 h-4 text-indigo-400" />
            <span>📊 DATA FINDINGS</span>
            <span className="ml-auto text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              Deterministic Fact
            </span>
          </div>

          <div className="prose prose-sm prose-invert max-w-none text-slate-300 leading-relaxed text-xs md:text-sm">
            {parsed?.dataFindings ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.dataFindings}</ReactMarkdown>
            ) : (
              <ul className="space-y-1.5 list-disc pl-4">
                {dataFactsList.map((fact, idx) => (
                  <li key={idx} className="text-slate-300 font-medium">{fact}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* 2. DOCUMENT EVIDENCE SECTION */}
      {(parsed?.docEvidence || docChunks.length > 0) && (
        <div className="rounded-2xl bg-gradient-to-b from-emerald-950/30 to-slate-900/60 border border-emerald-500/30 p-4 shadow-xl backdrop-blur-md">
          <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-emerald-500/20 text-emerald-400 font-semibold text-xs tracking-wider uppercase">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span>📄 DOCUMENT EVIDENCE</span>
            </div>
            <button
              onClick={() => setDocPassagesOpen(!docPassagesOpen)}
              className="flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer"
            >
              <span>{docPassagesOpen ? 'Collapse' : 'Expand'}</span>
              {docPassagesOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {docPassagesOpen && (
            <div className="space-y-3">
              {docChunks.length > 0 ? (
                docChunks.map((chunk, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950/60 border border-emerald-500/20 text-xs text-slate-300">
                    <div className="flex items-center gap-2 mb-1.5 font-semibold text-emerald-300">
                      <Layers className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      <span>{chunk.filename || 'Document.pdf'}</span>
                      <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
                        Page {chunk.page || 1}
                      </span>
                    </div>
                    <p className="italic text-slate-300/90 leading-relaxed whitespace-pre-wrap pl-2 border-l-2 border-emerald-500/30">
                      "{chunk.text?.trim()}"
                    </p>
                  </div>
                ))
              ) : (
                <div className="prose prose-sm prose-invert max-w-none text-slate-300 leading-relaxed text-xs md:text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.docEvidence}</ReactMarkdown>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 3. AI INTERPRETATION SECTION */}
      {parsed?.interpretation && (
        <div className="rounded-2xl bg-gradient-to-b from-purple-950/30 to-slate-900/60 border border-purple-500/30 p-4 shadow-xl backdrop-blur-md">
          <div className="flex items-center gap-2 pb-2.5 mb-3 border-b border-purple-500/20 text-purple-400 font-semibold text-xs tracking-wider uppercase">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span>⚡ AI INTERPRETATION</span>
            <span className="ml-auto text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
              Grounded Synthesis
            </span>
          </div>

          <div className="prose prose-sm prose-invert max-w-none text-slate-200 leading-relaxed text-xs md:text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.interpretation}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* If not hybrid but standard answer wasn't parsed into data findings/evidence */}
      {!parsed?.dataFindings && !parsed?.interpretation && (
        <div className="prose prose-sm prose-invert max-w-none text-slate-300 leading-relaxed text-xs md:text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
        </div>
      )}

      {/* 4. CITATIONS SECTION */}
      {(parsed?.citations || citationsList.length > 0) && (
        <div className="rounded-xl bg-slate-950/50 border border-slate-700/50 p-3 shadow-md">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 mb-2">
            <ExternalLink className="w-3.5 h-3.5" />
            <span>🔗 CITATIONS & VERIFIED SOURCES</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {citationsList.length > 0 ? (
              citationsList.map((cite, idx) => (
                <div 
                  key={idx} 
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-[11px] text-indigo-200 font-mono shadow-sm"
                >
                  <FileText className="w-3 h-3 text-indigo-400" />
                  <span>{cite}</span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.citations}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Warnings / Fallback Alerts */}
      {Array.isArray(rawResponse?.warnings) && rawResponse.warnings.length > 0 && (
        <div className="text-xs text-amber-400/80 bg-amber-500/5 border border-amber-500/20 rounded-lg p-2.5 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>{rawResponse.warnings.join(' • ')}</span>
        </div>
      )}
    </div>
  );
};

export default StructuredResponse;

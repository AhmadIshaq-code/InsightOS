import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { 
  UploadCloud, 
  FileText, 
  Database, 
  Trash2, 
  Loader2, 
  Eye, 
  CheckCircle, 
  AlertTriangle, 
  Table as TableIcon,
  X,
  TrendingUp,
  BarChart2,
  LayoutDashboard,
  Search,
  BookOpen
} from 'lucide-react';
import { useFileUpload } from '../hooks/useFileUpload';
import { 
  uploadDatasetToBackend, 
  fetchDatasetsFromBackend, 
  fetchDatasetProfile, 
  fetchDatasetPreview, 
  fetchDatasetKPIs,
  removeDatasetFromBackend,
  searchDocumentsFromBackend
} from '../services/groqService';

const UploadPage = () => {
  const navigate = useNavigate();
  // Tab state: 'datasets' (CSV/Excel) vs 'documents' (PDF)
  const [activeTab, setActiveTab] = useState('datasets');

  // PDF Document context state (from useFileUpload)
  const { uploadFile, files: pdfFiles, removeFile: removePdfFile } = useFileUpload();

  // Document Semantic Search preview state
  const [docSearchQuery, setDocSearchQuery] = useState('');
  const [docSearchResults, setDocSearchResults] = useState(null);
  const [isSearchingDocs, setIsSearchingDocs] = useState(false);
  const [docSearchError, setDocSearchError] = useState(null);

  // Structured Datasets state
  const [datasets, setDatasets] = useState([]);
  const [isUploadingDataset, setIsUploadingDataset] = useState(false);
  const [datasetError, setDatasetError] = useState(null);
  const [datasetSuccess, setDatasetSuccess] = useState(null);

  // Inspected dataset modal / details state
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [selectedPreview, setSelectedPreview] = useState(null);
  const [selectedKpis, setSelectedKpis] = useState(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Load existing datasets on mount
  const loadDatasets = useCallback(async () => {
    try {
      const data = await fetchDatasetsFromBackend();
      setDatasets(data);
    } catch (err) {
      console.error("Failed to fetch datasets:", err);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  // Handle Dataset Upload (CSV / Excel)
  const handleDatasetDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setDatasetError("Invalid file type. Please upload a CSV, XLSX, or XLS file.");
      return;
    }

    setIsUploadingDataset(true);
    setDatasetError(null);
    setDatasetSuccess(null);

    try {
      const result = await uploadDatasetToBackend(file);
      setDatasetSuccess(`Successfully ingested & profiled ${file.name}`);
      await loadDatasets();
      // Auto inspect the newly uploaded dataset
      if (result?.dataset?.dataset_id) {
        inspectDataset(result.dataset.dataset_id);
      }
    } catch (err) {
      setDatasetError(err.message || "Failed to upload dataset.");
    } finally {
      setIsUploadingDataset(false);
    }
  }, [loadDatasets]);

  // Dropzone for Datasets
  const datasetDropzone = useDropzone({
    onDrop: handleDatasetDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false
  });

  // Dropzone for PDF Documents
  const documentDropzone = useDropzone({
    onDrop: (accepted) => accepted.forEach(file => uploadFile(file)),
    accept: { 'application/pdf': ['.pdf'] }
  });

  // Inspect Dataset Profile, Preview & Data Brain KPIs
  const inspectDataset = async (datasetId) => {
    setIsLoadingDetails(true);
    setSelectedProfile(null);
    setSelectedPreview(null);
    setSelectedKpis(null);
    try {
      const [profile, preview, kpis] = await Promise.all([
        fetchDatasetProfile(datasetId),
        fetchDatasetPreview(datasetId, 15),
        fetchDatasetKPIs(datasetId).catch((err) => {
          console.warn("Failed to fetch KPIs:", err);
          return null;
        })
      ]);
      setSelectedProfile(profile);
      setSelectedPreview(preview);
      setSelectedKpis(kpis);
    } catch (err) {
      setDatasetError(err.message || "Failed to load dataset details.");
    } finally {
      setIsLoadingDetails(false);
    }
  };

  // Delete Dataset
  const handleDeleteDataset = async (datasetId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this dataset?")) return;
    try {
      await removeDatasetFromBackend(datasetId);
      if (selectedProfile?.dataset?.dataset_id === datasetId) {
        setSelectedProfile(null);
        setSelectedPreview(null);
        setSelectedKpis(null);
      }
      await loadDatasets();
    } catch (err) {
      setDatasetError(err.message || "Failed to delete dataset.");
    }
  };

  // Semantic Knowledge Search Handler
  const handleDocSearch = async (e) => {
    e?.preventDefault();
    if (!docSearchQuery.trim()) return;
    setIsSearchingDocs(true);
    setDocSearchError(null);
    try {
      const res = await searchDocumentsFromBackend(docSearchQuery.trim(), 4);
      setDocSearchResults(res.results || []);
    } catch (err) {
      setDocSearchError(err.message || "Failed to search documents.");
    } finally {
      setIsSearchingDocs(false);
    }
  };

  return (
    <div className="flex-1 p-6 md:p-10 overflow-y-auto custom-scrollbar">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-5">
          <div>
            <h1 className="text-3xl font-bold text-white mb-1">Universal Data Ingestion</h1>
            <p className="text-slate-400 text-sm">Upload structured tabular datasets or corporate knowledge base documents.</p>
          </div>

          {/* Tab Switcher */}
          <div className="flex bg-black/40 p-1 rounded-xl border border-white/10 shrink-0">
            <button
              onClick={() => setActiveTab('datasets')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'datasets'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Database className="w-4 h-4" />
              Datasets (CSV / Excel)
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'documents'
                  ? 'bg-indigo-600 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileText className="w-4 h-4" />
              Documents (PDF RAG)
            </button>
          </div>
        </div>

        {/* ========================================================= */}
        {/* TAB 1: DATASETS (CSV / XLSX / XLS)                        */}
        {/* ========================================================= */}
        {activeTab === 'datasets' && (
          <div className="space-y-6">
            
            {/* Upload Zone */}
            <div 
              {...datasetDropzone.getRootProps()} 
              className={`glass-card rounded-3xl p-10 text-center cursor-pointer transition-all border-2 border-dashed ${
                datasetDropzone.isDragActive 
                  ? 'border-indigo-500 bg-indigo-500/10' 
                  : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/5'
              }`}
            >
              <input {...datasetDropzone.getInputProps()} />
              {isUploadingDataset ? (
                <div className="flex flex-col items-center justify-center py-4">
                  <Loader2 className="w-12 h-12 text-indigo-400 animate-spin mb-3" />
                  <p className="text-white font-medium">Profiling dataset with Pandas...</p>
                  <p className="text-slate-400 text-xs mt-1">Calculating statistics, quality score & schema</p>
                </div>
              ) : (
                <>
                  <UploadCloud className="w-14 h-14 text-indigo-400 mx-auto mb-3 opacity-90" />
                  <h3 className="text-lg font-bold text-white mb-1">Drag & Drop Structured Dataset Here</h3>
                  <p className="text-slate-400 text-sm mb-3">Supports CSV, XLSX, and XLS up to 50MB</p>
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-indigo-300 font-medium">
                    Auto-generates deterministic profile, quality metrics & schema
                  </span>
                </>
              )}
            </div>

            {/* Error / Success Notifications */}
            {datasetError && (
              <div className="flex items-center gap-3 p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-300 text-sm">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>{datasetError}</span>
              </div>
            )}
            {datasetSuccess && (
              <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-emerald-300 text-sm">
                <CheckCircle className="w-5 h-5 shrink-0" />
                <span>{datasetSuccess}</span>
              </div>
            )}

            {/* Uploaded Datasets List */}
            {datasets.length > 0 && (
              <div className="glass-card rounded-3xl p-6 space-y-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="w-4 h-4 text-indigo-400" />
                  Ingested Datasets ({datasets.length})
                </h3>

                <div className="grid grid-cols-1 gap-3">
                  {datasets.map((d) => {
                    const isSelected = selectedProfile?.dataset?.dataset_id === d.dataset_id;
                    return (
                      <div 
                        key={d.dataset_id}
                        onClick={() => inspectDataset(d.dataset_id)}
                        className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${
                          isSelected 
                            ? 'bg-indigo-600/15 border-indigo-500/40 ring-1 ring-indigo-500/30' 
                            : 'bg-black/30 border-white/5 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center gap-3.5 min-w-0">
                          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs uppercase shrink-0">
                            {d.file_type}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-white truncate">{d.original_filename}</p>
                            <p className="text-xs text-slate-400 mt-0.5">
                              {d.row_count?.toLocaleString()} rows &bull; {d.column_count} columns &bull; {(d.file_size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 shrink-0">
                          {/* Quality Score Badge */}
                          <div className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                            (d.quality_score ?? 100) >= 90
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : (d.quality_score ?? 100) >= 75
                              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                              : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                          }`}>
                            Score: {d.quality_score ?? 100}%
                          </div>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/dashboard/${d.dataset_id}`);
                            }}
                            className="px-2.5 py-1.5 text-xs font-semibold rounded-xl bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 transition-all flex items-center gap-1.5"
                            title="Open in Executive Dashboard"
                          >
                            <LayoutDashboard className="w-3.5 h-3.5" />
                            <span className="hidden sm:inline">Dashboard</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); inspectDataset(d.dataset_id); }}
                            className="p-2 text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-all"
                            title="Inspect Profile"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleDeleteDataset(d.dataset_id, e)}
                            className="p-2 text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all"
                            title="Delete Dataset"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Dataset Details & Profile Panel */}
            {isLoadingDetails && (
              <div className="glass-card rounded-3xl p-12 text-center">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-2" />
                <p className="text-sm text-slate-300">Loading dataset profile & preview...</p>
              </div>
            )}

            {selectedProfile && !isLoadingDetails && (
              <div className="glass-card rounded-3xl p-6 space-y-6 border border-indigo-500/20">
                {/* Profile Header */}
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <TableIcon className="w-5 h-5 text-indigo-400" />
                      Dataset Profile: {selectedProfile.dataset.original_filename}
                    </h3>
                    <p className="text-xs text-slate-400">
                      ID: {selectedProfile.dataset.dataset_id} &bull; Uploaded: {new Date(selectedProfile.dataset.upload_timestamp).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigate(`/dashboard/${selectedProfile.dataset.dataset_id}`)}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-1.5 cursor-pointer"
                    >
                      <LayoutDashboard className="w-3.5 h-3.5" />
                      <span>Executive Dashboard</span>
                    </button>
                    <button
                      onClick={() => { setSelectedProfile(null); setSelectedPreview(null); }}
                      className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 cursor-pointer"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {/* Quality Metrics Grid */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Deterministic Data Quality</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-black/40 border border-white/5 p-3.5 rounded-2xl">
                      <p className="text-xs text-slate-400">Quality Score</p>
                      <p className="text-xl font-bold text-emerald-400 mt-1">{selectedProfile.quality.score}%</p>
                    </div>
                    <div className="bg-black/40 border border-white/5 p-3.5 rounded-2xl">
                      <p className="text-xs text-slate-400">Missing Cells</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {selectedProfile.quality.missing_cells} <span className="text-xs font-normal text-slate-400">({selectedProfile.quality.missing_percentage}%)</span>
                      </p>
                    </div>
                    <div className="bg-black/40 border border-white/5 p-3.5 rounded-2xl">
                      <p className="text-xs text-slate-400">Duplicate Rows</p>
                      <p className="text-xl font-bold text-white mt-1">
                        {selectedProfile.quality.duplicate_rows} <span className="text-xs font-normal text-slate-400">({selectedProfile.quality.duplicate_percentage}%)</span>
                      </p>
                    </div>
                    <div className="bg-black/40 border border-white/5 p-3.5 rounded-2xl">
                      <p className="text-xs text-slate-400">Empty Columns</p>
                      <p className="text-xl font-bold text-white mt-1">{selectedProfile.quality.empty_columns}</p>
                    </div>
                  </div>
                </div>

                {/* Column Schema & Semantic Types */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                    Schema & Semantic Columns ({selectedProfile.columns.length})
                  </h4>
                  <div className="overflow-x-auto custom-scrollbar border border-white/5 rounded-2xl bg-black/40">
                    <table className="w-full text-left text-xs text-slate-300">
                      <thead className="bg-white/5 text-slate-400 uppercase font-semibold border-b border-white/5">
                        <tr>
                          <th className="py-3 px-4">Column Name</th>
                          <th className="py-3 px-4">Semantic Type</th>
                          <th className="py-3 px-4">Pandas Dtype</th>
                          <th className="py-3 px-4">Nulls (%)</th>
                          <th className="py-3 px-4">Unique Values</th>
                          <th className="py-3 px-4">Key Stats / Samples</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {selectedProfile.columns.map((col) => (
                          <tr key={col.name} className="hover:bg-white/5">
                            <td className="py-2.5 px-4 font-medium text-white">{col.name}</td>
                            <td className="py-2.5 px-4">
                              <span className={`px-2 py-0.5 rounded-full font-semibold uppercase text-[10px] ${
                                col.semantic_type === 'numeric'
                                  ? 'bg-blue-500/20 text-blue-300'
                                  : col.semantic_type === 'categorical'
                                  ? 'bg-purple-500/20 text-purple-300'
                                  : col.semantic_type === 'datetime'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : col.semantic_type === 'boolean'
                                  ? 'bg-amber-500/20 text-amber-300'
                                  : 'bg-slate-700 text-slate-300'
                              }`}>
                                {col.semantic_type}
                              </span>
                            </td>
                            <td className="py-2.5 px-4 font-mono text-slate-400">{col.pandas_dtype}</td>
                            <td className="py-2.5 px-4 text-slate-300">{col.null_count} ({col.null_percentage}%)</td>
                            <td className="py-2.5 px-4 text-slate-300">{col.unique_count}</td>
                            <td className="py-2.5 px-4 text-slate-400 max-w-xs truncate">
                              {col.numeric_stats ? (
                                <span>min: {col.numeric_stats.min}, max: {col.numeric_stats.max}, mean: {col.numeric_stats.mean}</span>
                              ) : col.datetime_stats ? (
                                <span>range: {col.datetime_stats.range_days} days</span>
                              ) : col.sample_values ? (
                                <span>{col.sample_values.join(', ')}</span>
                              ) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Data Brain Deterministic KPIs & Analytics Section */}
                {selectedKpis && (
                  <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-2xl p-5 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-500/20 pb-3">
                      <div className="flex items-center gap-2">
                        <BarChart2 className="w-4 h-4 text-indigo-400" />
                        <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                          Data Brain Deterministic KPIs
                        </h4>
                      </div>
                      <span className="text-[11px] text-indigo-300/80 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
                        Zero LLM Hallucinations &bull; Controlled Python/Pandas
                      </span>
                    </div>

                    {/* Excluded ID columns notice if any */}
                    {selectedKpis.excluded_id_columns && selectedKpis.excluded_id_columns.length > 0 && (
                      <p className="text-xs text-slate-400 italic">
                        Identifier columns excluded from business KPIs:{" "}
                        <span className="text-amber-400/90 font-mono">
                          {selectedKpis.excluded_id_columns.join(", ")}
                        </span>
                      </p>
                    )}

                    {/* KPI cards grid */}
                    {selectedKpis.kpis && Object.keys(selectedKpis.kpis).length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {Object.entries(selectedKpis.kpis).map(([metricName, metric]) => (
                          <div key={metricName} className="bg-black/40 border border-white/5 rounded-xl p-3.5 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-white truncate">{metricName}</span>
                              <span className="text-[10px] text-slate-400 font-mono">{metric.count} rows</span>
                            </div>
                            <div className="flex items-baseline justify-between">
                              <span className="text-xs text-slate-400">Total:</span>
                              <span className="text-sm font-semibold text-emerald-400 font-mono">
                                {typeof metric.total === 'number' ? metric.total.toLocaleString(undefined, { maximumFractionDigits: 2 }) : metric.total}
                              </span>
                            </div>
                            <div className="flex items-baseline justify-between">
                              <span className="text-xs text-slate-400">Average:</span>
                              <span className="text-sm font-semibold text-blue-400 font-mono">
                                {typeof metric.average === 'number' ? metric.average.toLocaleString(undefined, { maximumFractionDigits: 2 }) : metric.average}
                              </span>
                            </div>
                            <div className="grid grid-cols-3 gap-1 pt-1.5 border-t border-white/5 text-[10px] text-slate-400">
                              <div>Min: <span className="font-mono text-slate-300">{metric.minimum}</span></div>
                              <div className="text-center">Med: <span className="font-mono text-slate-300">{metric.median}</span></div>
                              <div className="text-right">Max: <span className="font-mono text-slate-300">{metric.maximum}</span></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400">No non-identifier numeric columns found for business KPI calculation.</p>
                    )}
                  </div>
                )}

                {/* Safe Preview Table */}
                {selectedPreview && selectedPreview.preview_rows.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                      Safe Data Preview (First {selectedPreview.preview_rows.length} of {selectedPreview.total_rows} rows)
                    </h4>
                    <div className="overflow-x-auto custom-scrollbar border border-white/5 rounded-2xl bg-black/40 max-h-72">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-white/5 text-slate-400 uppercase font-semibold sticky top-0 border-b border-white/5">
                          <tr>
                            {selectedPreview.columns.map(c => (
                              <th key={c} className="py-2.5 px-4 whitespace-nowrap">{c}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                          {selectedPreview.preview_rows.map((row, idx) => (
                            <tr key={idx} className="hover:bg-white/5">
                              {selectedPreview.columns.map(c => (
                                <td key={c} className="py-2 px-4 whitespace-nowrap text-slate-300">
                                  {row[c] !== null && row[c] !== undefined ? String(row[c]) : <span className="text-slate-600 italic">null</span>}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: DOCUMENTS (PDF RAG) - PRESERVED                    */}
        {/* ========================================================= */}
        {activeTab === 'documents' && (
          <div className="space-y-6">
            <div 
              {...documentDropzone.getRootProps()} 
              className={`glass-card rounded-3xl p-10 text-center cursor-pointer transition-all border-2 border-dashed ${
                documentDropzone.isDragActive 
                  ? 'border-indigo-500 bg-indigo-500/10' 
                  : 'border-white/10 hover:border-indigo-500/50 hover:bg-white/5'
              }`}
            >
              <input {...documentDropzone.getInputProps()} />
              <UploadCloud className="w-14 h-14 text-indigo-400 mx-auto mb-3 opacity-90" />
              <h3 className="text-lg font-bold text-white mb-1">Drag & Drop Corporate PDF Documents</h3>
              <p className="text-slate-400 text-sm">Upload policy handbooks, SOPs, and guidelines for semantic RAG search</p>
            </div>

            {pdfFiles.length > 0 && (
              <div className="glass-card rounded-3xl p-6 space-y-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  Indexed Knowledge Documents ({pdfFiles.length})
                </h3>
                <div className="space-y-3">
                  {pdfFiles.map((file) => (
                    <div key={file.id || file.document_id} className="flex items-center gap-4 bg-black/40 p-4 rounded-xl border border-white/5 hover:border-white/10 transition-all">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-xs uppercase shrink-0">
                        PDF
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white truncate">{file.name || file.filename}</p>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mt-1">
                          <span>{((file.size || file.file_size_bytes || 0) / 1024).toFixed(1)} KB</span>
                          {file.page_count ? (
                            <>
                              <span>&bull;</span>
                              <span className="text-indigo-300">{file.page_count} {file.page_count === 1 ? 'Page' : 'Pages'}</span>
                            </>
                          ) : null}
                          {file.chunk_count ? (
                            <>
                              <span>&bull;</span>
                              <span className="text-slate-300">{file.chunk_count} Chunks</span>
                            </>
                          ) : null}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {file.status === 'Processing...' || file.status === 'uploading' ? (
                          <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400 bg-amber-400/10 px-3 py-1 rounded-full border border-amber-400/20">
                            <Loader2 className="w-3 h-3 animate-spin" /> Indexing...
                          </div>
                        ) : (
                          <div className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full border border-emerald-400/20 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" /> Indexed in Chroma
                          </div>
                        )}
                        <button 
                          onClick={() => removePdfFile(file)}
                          disabled={file.status === 'Processing...' || file.status === 'uploading'}
                          className="p-2 text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors disabled:opacity-50"
                          title="Remove Document"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Document Semantic Search Testing Widget */}
            <div className="glass-card rounded-3xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Search className="w-4 h-4 text-indigo-400" />
                    Knowledge Brain Semantic Search Preview
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">Test vector retrieval, similarity scores, and page-level chunk grounding.</p>
                </div>
              </div>

              <form onSubmit={handleDocSearch} className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={docSearchQuery}
                    onChange={(e) => setDocSearchQuery(e.target.value)}
                    placeholder="Search documents (e.g. 'What is the vacation policy?' or 'Data breach protocol')..."
                    className="w-full pl-10 pr-4 py-2.5 bg-black/40 border border-white/10 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isSearchingDocs || !docSearchQuery.trim()}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors flex items-center gap-2 shrink-0"
                >
                  {isSearchingDocs ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
                  <span>Search</span>
                </button>
              </form>

              {docSearchError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{docSearchError}</span>
                </div>
              )}

              {docSearchResults && (
                <div className="space-y-3 pt-2">
                  <p className="text-xs text-slate-400 font-medium">
                    Found {docSearchResults.length} relevant chunk{docSearchResults.length === 1 ? '' : 's'}:
                  </p>
                  {docSearchResults.length === 0 ? (
                    <div className="p-4 rounded-xl bg-black/30 border border-white/5 text-center text-xs text-slate-400">
                      No matching passages found.
                    </div>
                  ) : (
                    docSearchResults.map((result, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl bg-black/30 border border-white/5 space-y-2">
                        <div className="flex items-center justify-between gap-2 text-xs">
                          <span className="font-semibold text-indigo-300 flex items-center gap-1.5 truncate">
                            <FileText className="w-3.5 h-3.5 shrink-0" />
                            {result.filename} &bull; Page {result.page}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-300 font-mono text-[11px] shrink-0">
                            Relevance: {result.relevance_score !== null ? result.relevance_score : 'N/A'}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed bg-black/20 p-2.5 rounded-lg font-sans border border-white/5">
                          {result.text}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default UploadPage;

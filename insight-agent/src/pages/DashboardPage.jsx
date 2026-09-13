import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  TrendingUp,
  BarChart2,
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Calendar,
  ChevronDown,
  Hash,
  Percent,
  Filter,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Sparkles,
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  ShieldAlert,
  TrendingDown,
  Sliders,
  Search
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import {
  fetchDatasets,
  fetchDatasetSummary,
  fetchDatasetKPIs,
  fetchDatasetTop,
  fetchDatasetBottom,
  fetchDatasetTrend,
  fetchDatasetAnomalies,
  fetchDatasetForecast
} from '../services/datasetService';

const CustomChartTooltip = ({ active, payload, label, prefix = '', suffix = '' }) => {
  if (active && payload && payload.length) {
    const item = payload[0];
    const val = typeof item.value === 'number' 
      ? item.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) 
      : item.value;
    return (
      <div className="bg-slate-900/95 border border-indigo-500/30 rounded-xl p-3 shadow-2xl backdrop-blur-md">
        <p className="text-xs font-semibold text-slate-300 mb-1">{label}</p>
        <p className="text-sm font-bold text-indigo-300 flex items-center gap-1.5 font-mono">
          <span>{prefix}</span>
          <span>{val}</span>
          <span>{suffix}</span>
        </p>
      </div>
    );
  }
  return null;
};

const ForecastChartTooltip = ({ active, payload, label, prefix = '', suffix = '' }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900/95 border border-purple-500/30 rounded-xl p-3 shadow-2xl backdrop-blur-md min-w-[180px]">
        <p className="text-xs font-semibold text-slate-300 mb-2 border-b border-white/10 pb-1 flex items-center justify-between">
          <span>Period: {label}</span>
        </p>
        <div className="space-y-1.5">
          {payload.map((item, idx) => {
            if (item.value === null || item.value === undefined) return null;
            const isForecast = item.dataKey === 'forecast';
            const valStr = typeof item.value === 'number'
              ? item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
              : item.value;
            return (
              <div key={idx} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-slate-300">
                  <span className={`w-2 h-2 rounded-full ${isForecast ? 'bg-purple-400' : 'bg-indigo-400'}`} />
                  <span>{isForecast ? 'Projected Forecast' : 'Historical Value'}:</span>
                </span>
                <span className={`font-mono font-bold ${isForecast ? 'text-purple-300' : 'text-indigo-300'}`}>
                  {prefix}{valStr}{suffix}
                  {isForecast && <span className="ml-1 text-[10px] text-purple-400 font-sans font-normal">(est.)</span>}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  return null;
};

const DashboardPage = () => {
  const { datasetId: paramDatasetId } = useParams();
  const navigate = useNavigate();

  // Dataset List & Active Selection State
  const [datasets, setDatasets] = useState([]);
  const [activeDatasetId, setActiveDatasetId] = useState(paramDatasetId || null);
  const [activeDatasetMeta, setActiveDatasetMeta] = useState(null);

  // Loading & Global Error States
  const [isInitializing, setIsInitializing] = useState(true);
  const [datasetNotFoundError, setDatasetNotFoundError] = useState(false);
  const [globalError, setGlobalError] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Data Brain Core State
  const [summary, setSummary] = useState(null);
  const [kpisData, setKpisData] = useState(null);

  // Business Metric Spotlight State (Anti-Explosion)
  const [selectedBusinessMetric, setSelectedBusinessMetric] = useState('');

  // Trend Widget State & Stale-Response Guards
  const [trendDateCol, setTrendDateCol] = useState('');
  const [trendMetricCol, setTrendMetricCol] = useState('');
  const [trendAgg, setTrendAgg] = useState('sum');
  const [trendFreq, setTrendFreq] = useState('auto');
  const [trendData, setTrendData] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState(null);
  const trendAbortRef = useRef(null);
  const trendSeqRef = useRef(0);

  // Category Widget State & Stale-Response Guards
  const [catCategoryCol, setCatCategoryCol] = useState('');
  const [catMetricCol, setCatMetricCol] = useState('');
  const [catAgg, setCatAgg] = useState('sum');
  const [catLimit, setCatLimit] = useState(5);
  const [catData, setCatData] = useState(null);
  const [catLoading, setCatLoading] = useState(false);
  const [catError, setCatError] = useState(null);
  const catAbortRef = useRef(null);
  const catSeqRef = useRef(0);

  // Bottom Performers State & Stale-Response Guards
  const [bottomData, setBottomData] = useState(null);
  const [bottomLoading, setBottomLoading] = useState(false);
  const [bottomError, setBottomError] = useState(null);
  const bottomAbortRef = useRef(null);
  const bottomSeqRef = useRef(0);

  // ==========================================
  // Intelligence: Anomaly Detection State
  // ==========================================
  const [anomalyMetricCol, setAnomalyMetricCol] = useState('');
  const [anomalyDateCol, setAnomalyDateCol] = useState('');
  const [anomalyDimCol, setAnomalyDimCol] = useState('');
  const [anomalyLimit, setAnomalyLimit] = useState(20);
  const [anomalyData, setAnomalyData] = useState(null);
  const [anomalyLoading, setAnomalyLoading] = useState(false);
  const [anomalyError, setAnomalyError] = useState(null);
  const anomalyAbortRef = useRef(null);
  const anomalySeqRef = useRef(0);

  // ==========================================
  // Intelligence: Time-Series Forecast State
  // ==========================================
  const [forecastMetricCol, setForecastMetricCol] = useState('');
  const [forecastDateCol, setForecastDateCol] = useState('');
  const [forecastPeriods, setForecastPeriods] = useState(3);
  const [forecastFreq, setForecastFreq] = useState('auto');
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState(null);
  const forecastAbortRef = useRef(null);
  const forecastSeqRef = useRef(0);

  // 1. Initial Load: Fetch available datasets
  const initDatasets = useCallback(async () => {
    setIsInitializing(true);
    setGlobalError(null);
    setDatasetNotFoundError(false);

    try {
      const list = await fetchDatasets();
      setDatasets(list);

      if (list.length === 0) {
        setActiveDatasetId(null);
        setActiveDatasetMeta(null);
        setIsInitializing(false);
        return;
      }

      // If URL param provided, find matching dataset
      if (paramDatasetId) {
        const found = list.find((d) => d.dataset_id === paramDatasetId);
        if (found) {
          setActiveDatasetId(found.dataset_id);
          setActiveDatasetMeta(found);
        } else {
          setDatasetNotFoundError(true);
          setActiveDatasetId(paramDatasetId);
        }
      } else {
        // Deterministically select latest dataset
        const latest = list[0];
        setActiveDatasetId(latest.dataset_id);
        setActiveDatasetMeta(latest);
      }
    } catch (err) {
      setGlobalError(err.message || 'Failed to load datasets.');
    } finally {
      setIsInitializing(false);
    }
  }, [paramDatasetId]);

  useEffect(() => {
    initDatasets();
  }, [initDatasets]);

  // Handle dataset switching
  const handleSelectDataset = (id) => {
    if (id === activeDatasetId) return;
    navigate(`/dashboard/${id}`);
  };

  // 2. Load Core Dataset Overview & KPIs
  const loadDatasetData = useCallback(async (id) => {
    if (!id || datasetNotFoundError) return;

    // Abort any ongoing widget requests
    if (trendAbortRef.current) trendAbortRef.current.abort();
    if (catAbortRef.current) catAbortRef.current.abort();
    if (bottomAbortRef.current) bottomAbortRef.current.abort();
    if (anomalyAbortRef.current) anomalyAbortRef.current.abort();
    if (forecastAbortRef.current) forecastAbortRef.current.abort();

    setIsRefreshing(true);
    setGlobalError(null);

    try {
      const [sumRes, kpiRes] = await Promise.all([
        fetchDatasetSummary(id),
        fetchDatasetKPIs(id)
      ]);

      setSummary(sumRes);
      setKpisData(kpiRes);

      // Derive smart defaults deterministically (No LLM)
      const numericCols = sumRes.numeric_columns || [];
      const excludedIds = kpiRes.excluded_id_columns || [];
      const businessNumericCols = numericCols.filter((col) => !excludedIds.includes(col));
      const candidateNumeric = businessNumericCols.length > 0 ? businessNumericCols : numericCols;

      const candidateCat = sumRes.categorical_columns || [];
      const candidateDate = sumRes.datetime_columns || [];

      // Set business metric default
      const defaultMetric = candidateNumeric[0] || '';
      setSelectedBusinessMetric(defaultMetric);

      // Set trend defaults
      setTrendDateCol(candidateDate[0] || '');
      setTrendMetricCol(defaultMetric);
      setTrendAgg('sum');
      setTrendFreq('auto');

      // Set category comparison defaults
      setCatCategoryCol(candidateCat[0] || '');
      setCatMetricCol(defaultMetric);
      setCatAgg('sum');
      setCatLimit(5);

      // Set anomaly detection defaults
      setAnomalyMetricCol(defaultMetric);
      setAnomalyDateCol(candidateDate[0] || '');
      setAnomalyDimCol(candidateCat[0] || '');
      setAnomalyLimit(20);
      setAnomalyData(null);
      setAnomalyError(null);

      // Set forecast defaults
      setForecastMetricCol(defaultMetric);
      setForecastDateCol(candidateDate[0] || '');
      setForecastPeriods(3);
      setForecastFreq('auto');
      setForecastData(null);
      setForecastError(null);
    } catch (err) {
      if (err.message && err.message.includes('not found')) {
        setDatasetNotFoundError(true);
      } else {
        setGlobalError(err.message || 'Failed to load dataset insights.');
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [datasetNotFoundError]);

  useEffect(() => {
    if (activeDatasetId && !datasetNotFoundError) {
      loadDatasetData(activeDatasetId);
    }
  }, [activeDatasetId, datasetNotFoundError, loadDatasetData]);

  // 3. Dynamic Trend Widget Fetch with Race Condition Guard
  const fetchTrend = useCallback(async () => {
    if (!activeDatasetId || !trendDateCol || !trendMetricCol) {
      setTrendData(null);
      return;
    }

    if (trendAbortRef.current) {
      trendAbortRef.current.abort();
    }
    const abortController = new AbortController();
    trendAbortRef.current = abortController;

    const currentSeq = ++trendSeqRef.current;
    setTrendLoading(true);
    setTrendError(null);

    try {
      const res = await fetchDatasetTrend(
        activeDatasetId,
        {
          date_column: trendDateCol,
          metric_column: trendMetricCol,
          aggregation: trendAgg,
          frequency: trendFreq
        },
        { signal: abortController.signal }
      );

      // Discard stale responses
      if (currentSeq === trendSeqRef.current) {
        setTrendData(res);
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled') return;
      if (currentSeq === trendSeqRef.current) {
        setTrendError(err.message || 'Failed to load trend data.');
      }
    } finally {
      if (currentSeq === trendSeqRef.current) {
        setTrendLoading(false);
      }
    }
  }, [activeDatasetId, trendDateCol, trendMetricCol, trendAgg, trendFreq]);

  useEffect(() => {
    fetchTrend();
  }, [fetchTrend]);

  // 4. Dynamic Category Widget Fetch with Race Condition Guard
  const fetchCategoryCharts = useCallback(async () => {
    if (!activeDatasetId || !catCategoryCol || !catMetricCol) {
      setCatData(null);
      setBottomData(null);
      return;
    }

    // Top categories
    if (catAbortRef.current) catAbortRef.current.abort();
    const catAbort = new AbortController();
    catAbortRef.current = catAbort;
    const catSeq = ++catSeqRef.current;

    setCatLoading(true);
    setCatError(null);

    // Bottom categories
    if (bottomAbortRef.current) bottomAbortRef.current.abort();
    const botAbort = new AbortController();
    bottomAbortRef.current = botAbort;
    const botSeq = ++bottomSeqRef.current;

    setBottomLoading(true);
    setBottomError(null);

    // Run parallel fetches with isolated error handling
    fetchDatasetTop(
      activeDatasetId,
      {
        category_column: catCategoryCol,
        metric_column: catMetricCol,
        aggregation: catAgg,
        limit: catLimit
      },
      { signal: catAbort.signal }
    )
      .then((res) => {
        if (catSeq === catSeqRef.current) {
          setCatData(res);
          setCatLoading(false);
        }
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.message === 'canceled') return;
        if (catSeq === catSeqRef.current) {
          setCatError(err.message || 'Failed to load category ranking.');
          setCatLoading(false);
        }
      });

    fetchDatasetBottom(
      activeDatasetId,
      {
        category_column: catCategoryCol,
        metric_column: catMetricCol,
        aggregation: catAgg,
        limit: catLimit
      },
      { signal: botAbort.signal }
    )
      .then((res) => {
        if (botSeq === bottomSeqRef.current) {
          setBottomData(res);
          setBottomLoading(false);
        }
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.message === 'canceled') return;
        if (botSeq === bottomSeqRef.current) {
          setBottomError(err.message || 'Failed to load bottom performers.');
          setBottomLoading(false);
        }
      });
  }, [activeDatasetId, catCategoryCol, catMetricCol, catAgg, catLimit]);

  useEffect(() => {
    fetchCategoryCharts();
  }, [fetchCategoryCharts]);

  // Derived Business Metrics list for Spotlight
  const availableBusinessMetrics = useMemo(() => {
    if (!summary || !kpisData) return [];
    const allNumeric = summary.numeric_columns || [];
    const excluded = kpisData.excluded_id_columns || [];
    const filtered = allNumeric.filter((col) => !excluded.includes(col));
    return filtered.length > 0 ? filtered : allNumeric;
  }, [summary, kpisData]);

  // Selected metric's KPI values
  const activeMetricKpi = useMemo(() => {
    if (!kpisData?.kpis || !selectedBusinessMetric) return null;
    return kpisData.kpis[selectedBusinessMetric] || null;
  }, [kpisData, selectedBusinessMetric]);

  // ==========================================
  // Intelligence: Anomaly Detection Handler
  // ==========================================
  const handleDetectAnomalies = useCallback(async () => {
    if (!activeDatasetId || !anomalyMetricCol) {
      setAnomalyError('Please select a metric column for anomaly detection.');
      return;
    }

    if (anomalyAbortRef.current) {
      anomalyAbortRef.current.abort();
    }
    const abortController = new AbortController();
    anomalyAbortRef.current = abortController;

    const currentSeq = ++anomalySeqRef.current;
    setAnomalyLoading(true);
    setAnomalyError(null);

    try {
      const res = await fetchDatasetAnomalies(
        activeDatasetId,
        {
          metric_column: anomalyMetricCol,
          date_column: anomalyDateCol || null,
          dimension_column: anomalyDimCol || null,
          limit: anomalyLimit
        },
        { signal: abortController.signal }
      );

      if (currentSeq === anomalySeqRef.current) {
        setAnomalyData(res);
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled') return;
      if (currentSeq === anomalySeqRef.current) {
        setAnomalyError(err.message || 'Failed to detect anomalies.');
      }
    } finally {
      if (currentSeq === anomalySeqRef.current) {
        setAnomalyLoading(false);
      }
    }
  }, [activeDatasetId, anomalyMetricCol, anomalyDateCol, anomalyDimCol, anomalyLimit]);

  // ==========================================
  // Intelligence: Time-Series Forecast Handler
  // ==========================================
  const handleGenerateForecast = useCallback(async () => {
    if (!activeDatasetId || !forecastMetricCol) {
      setForecastError('Please select a numeric metric column for forecasting.');
      return;
    }
    if (!forecastDateCol) {
      setForecastError('A datetime column is required for deterministic time-series forecasting.');
      return;
    }

    if (forecastAbortRef.current) {
      forecastAbortRef.current.abort();
    }
    const abortController = new AbortController();
    forecastAbortRef.current = abortController;

    const currentSeq = ++forecastSeqRef.current;
    setForecastLoading(true);
    setForecastError(null);

    try {
      const res = await fetchDatasetForecast(
        activeDatasetId,
        {
          metric_column: forecastMetricCol,
          date_column: forecastDateCol,
          periods: forecastPeriods,
          frequency: forecastFreq === 'auto' ? null : forecastFreq
        },
        { signal: abortController.signal }
      );

      if (currentSeq === forecastSeqRef.current) {
        setForecastData(res);
      }
    } catch (err) {
      if (err.name === 'CanceledError' || err.message === 'canceled') return;
      if (currentSeq === forecastSeqRef.current) {
        setForecastError(err.message || 'Failed to generate time-series forecast.');
      }
    } finally {
      if (currentSeq === forecastSeqRef.current) {
        setForecastLoading(false);
      }
    }
  }, [activeDatasetId, forecastMetricCol, forecastDateCol, forecastPeriods, forecastFreq]);

  // Combined Forecast Chart Data (Historical + Projected)
  const combinedForecastChartData = useMemo(() => {
    if (!forecastData) return [];
    const points = [];

    // Historical points
    if (Array.isArray(forecastData.historical)) {
      forecastData.historical.forEach((h, idx) => {
        const isLastHistorical = idx === forecastData.historical.length - 1;
        points.push({
          period: h.period,
          historical: typeof h.value === 'number' ? h.value : null,
          forecast: isLastHistorical && typeof h.value === 'number' ? h.value : null,
          type: 'Historical'
        });
      });
    }

    // Forecast points
    if (Array.isArray(forecastData.forecast)) {
      forecastData.forecast.forEach((f) => {
        points.push({
          period: f.period,
          historical: null,
          forecast: typeof f.predicted_value === 'number' ? f.predicted_value : null,
          type: 'Projected'
        });
      });
    }

    return points;
  }, [forecastData]);

  // =========================================================================
  // VIEW 1: ZERO DATASETS AVAILABLE (Polished Empty State)
  // =========================================================================
  if (!isInitializing && datasets.length === 0) {
    return (
      <div className="flex-1 p-6 md:p-12 overflow-y-auto custom-scrollbar flex items-center justify-center">
        <div className="max-w-md w-full glass-card border border-white/10 rounded-3xl p-8 text-center space-y-6 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
            <Database className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">No Datasets Available</h2>
            <p className="text-slate-400 text-sm leading-relaxed">
              Upload a CSV or Excel file to unlock the InsightOS Executive Analytics Dashboard with deterministic KPIs, trend forecasts, and category rankings.
            </p>
          </div>
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 w-full py-3.5 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg shadow-indigo-600/30"
          >
            <UploadCloud className="w-5 h-5" />
            Upload Your First Dataset
          </Link>
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: DATASET NOT FOUND (404 Error State)
  // =========================================================================
  if (!isInitializing && datasetNotFoundError) {
    return (
      <div className="flex-1 p-6 md:p-12 overflow-y-auto custom-scrollbar flex items-center justify-center">
        <div className="max-w-md w-full glass-card border border-rose-500/20 rounded-3xl p-8 text-center space-y-6 shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Dataset Not Found</h2>
            <p className="text-slate-400 text-sm leading-relaxed">
              The requested dataset ID does not exist or may have been deleted from storage.
            </p>
          </div>
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 w-full py-3.5 px-6 rounded-xl bg-white/10 hover:bg-white/15 text-white font-semibold border border-white/10 transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
            Return to Datasets Management
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-5 md:p-8 overflow-y-auto custom-scrollbar space-y-6">
      
      {/* =================================================================== */}
      {/* 1. EXECUTIVE HEADER & DATASET SELECTOR                              */}
      {/* =================================================================== */}
      <div className="glass-card rounded-3xl p-6 border border-white/5 shadow-2xl backdrop-blur-md">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          
          {/* Branding & Dataset Identity */}
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20 shrink-0 mt-0.5">
              <LayoutDashboard className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
                  InsightOS Analytics
                </span>
                {summary && (
                  <span className="text-xs text-slate-400 font-mono">
                    ID: {summary.dataset_id?.slice(0, 8)}...
                  </span>
                )}
              </div>
              <h1 className="text-2xl md:text-3xl font-bold text-white mt-1">
                {summary ? summary.original_filename : 'Executive Analytics Dashboard'}
              </h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Deterministic business intelligence &bull; Zero LLM hallucinations &bull; Pandas engine
              </p>
            </div>
          </div>

          {/* Quick Actions & Dataset Switcher */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Dataset Selector Dropdown */}
            {datasets.length > 1 && (
              <div className="relative">
                <select
                  value={activeDatasetId || ''}
                  onChange={(e) => handleSelectDataset(e.target.value)}
                  className="bg-black/50 border border-white/10 hover:border-indigo-500/40 text-slate-200 text-xs font-medium rounded-xl py-2.5 pl-3.5 pr-8 focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none cursor-pointer"
                >
                  {datasets.map((d) => (
                    <option key={d.dataset_id} value={d.dataset_id} className="bg-slate-900 text-white">
                      {d.original_filename} ({d.file_type?.toUpperCase()})
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            )}

            {/* Refresh Button */}
            <button
              onClick={() => activeDatasetId && loadDatasetData(activeDatasetId)}
              disabled={isRefreshing}
              className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-slate-300 border border-white/5 transition-all disabled:opacity-50"
              title="Refresh Dashboard Facts"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
            </button>

            {/* Back to Datasets */}
            <Link
              to="/"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600/15 hover:bg-indigo-600/25 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-all"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Manage Datasets
            </Link>
          </div>
        </div>
      </div>

      {/* Global Error Banner if any */}
      {globalError && (
        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-4 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{globalError}</span>
        </div>
      )}

      {/* =================================================================== */}
      {/* 2. GLOBAL DATASET HEALTH & PROFILE METRICS                          */}
      {/* =================================================================== */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Total Rows */}
        <div className="glass-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Total Rows</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {summary ? summary.row_count.toLocaleString() : '-'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Data records loaded</div>
        </div>

        {/* Total Columns */}
        <div className="glass-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Columns</span>
            <Hash className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {summary ? summary.column_count : '-'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {summary ? `${summary.numeric_columns?.length || 0} numeric &bull; ${summary.categorical_columns?.length || 0} cat` : '-'}
          </div>
        </div>

        {/* Data Quality Score */}
        <div className="glass-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Quality Score</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono">
            {summary ? (
              <span className={
                summary.quality_score >= 90 ? 'text-emerald-400' :
                summary.quality_score >= 75 ? 'text-amber-400' : 'text-rose-400'
              }>
                {summary.quality_score}%
              </span>
            ) : '-'}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Deterministic health</div>
        </div>

        {/* Missing Cells */}
        <div className="glass-card rounded-2xl p-4 border border-white/5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Missing Cells</span>
            <Percent className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {summary ? summary.missing_percentage : 0}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {summary ? `${summary.missing_cells} cells null` : '-'}
          </div>
        </div>

        {/* Duplicate Rows */}
        <div className="glass-card rounded-2xl p-4 border border-white/5 col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Duplicates</span>
            <Filter className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {summary ? summary.duplicate_percentage : 0}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            {summary ? `${summary.duplicate_rows} duplicate rows` : '-'}
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* 3. BUSINESS METRIC SPOTLIGHT (Anti-Explosion Control)               */}
      {/* =================================================================== */}
      <div className="glass-card rounded-3xl p-6 border border-white/5 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
              $
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Business Metrics Spotlight</h2>
              <p className="text-xs text-slate-400">
                Authoritative calculations &bull; Excludes row identifiers &bull; Switch metric below
              </p>
            </div>
          </div>

          {/* Metric Selector Dropdown */}
          {availableBusinessMetrics.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Metric:</span>
              <div className="relative">
                <select
                  value={selectedBusinessMetric}
                  onChange={(e) => setSelectedBusinessMetric(e.target.value)}
                  className="bg-black/50 border border-indigo-500/30 text-indigo-300 text-xs font-semibold rounded-xl py-2 pl-3 pr-8 focus:outline-none focus:ring-1 focus:ring-indigo-500 appearance-none cursor-pointer"
                >
                  {availableBusinessMetrics.map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      {col}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-indigo-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          )}
        </div>

        {/* Quick Tabs for Top 4 Default Metrics if multiple exist */}
        {availableBusinessMetrics.length > 1 && (
          <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider shrink-0 mr-1">Quick Select:</span>
            {availableBusinessMetrics.slice(0, 5).map((metric) => (
              <button
                key={metric}
                onClick={() => setSelectedBusinessMetric(metric)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all shrink-0 ${
                  selectedBusinessMetric === metric
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
                }`}
              >
                {metric}
              </button>
            ))}
          </div>
        )}

        {/* Excluded Identifier Columns Tag */}
        {kpisData?.excluded_id_columns && kpisData.excluded_id_columns.length > 0 && (
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5 bg-black/30 border border-white/5 rounded-xl px-3 py-1.5 w-fit">
            <span className="text-amber-400 font-bold">&bull; Excluded ID Columns:</span>
            <span className="font-mono text-slate-300">
              {kpisData.excluded_id_columns.join(', ')}
            </span>
          </div>
        )}

        {/* Selected Metric Statistics Cards */}
        {activeMetricKpi ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 pt-1">
            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1">
              <span className="text-xs text-slate-400 font-medium">Total Sum</span>
              <div className="text-xl font-bold text-emerald-400 font-mono truncate">
                {typeof activeMetricKpi.total === 'number'
                  ? activeMetricKpi.total.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : activeMetricKpi.total}
              </div>
              <div className="text-[10px] text-slate-400">Sum over {activeMetricKpi.count} values</div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1">
              <span className="text-xs text-slate-400 font-medium">Average (Mean)</span>
              <div className="text-xl font-bold text-blue-400 font-mono truncate">
                {typeof activeMetricKpi.average === 'number'
                  ? activeMetricKpi.average.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : activeMetricKpi.average}
              </div>
              <div className="text-[10px] text-slate-400">Mean per record</div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1">
              <span className="text-xs text-slate-400 font-medium">Minimum</span>
              <div className="text-xl font-bold text-slate-200 font-mono truncate">
                {typeof activeMetricKpi.minimum === 'number'
                  ? activeMetricKpi.minimum.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : activeMetricKpi.minimum}
              </div>
              <div className="text-[10px] text-slate-400">Lowest value</div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1">
              <span className="text-xs text-slate-400 font-medium">Median</span>
              <div className="text-xl font-bold text-purple-400 font-mono truncate">
                {typeof activeMetricKpi.median === 'number'
                  ? activeMetricKpi.median.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : activeMetricKpi.median}
              </div>
              <div className="text-[10px] text-slate-400">50th percentile</div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1 col-span-2 sm:col-span-1">
              <span className="text-xs text-slate-400 font-medium">Maximum</span>
              <div className="text-xl font-bold text-amber-400 font-mono truncate">
                {typeof activeMetricKpi.maximum === 'number'
                  ? activeMetricKpi.maximum.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : activeMetricKpi.maximum}
              </div>
              <div className="text-[10px] text-slate-400">Peak value</div>
            </div>
          </div>
        ) : (
          <div className="bg-black/30 border border-white/5 rounded-2xl p-6 text-center text-slate-400 text-xs">
            Not enough numeric data for business KPI analysis in this dataset.
          </div>
        )}
      </div>

      {/* =================================================================== */}
      {/* 4. DYNAMIC ANALYTICS CHARTS AREA (Recharts with Race Protection)    */}
      {/* =================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* ----------------------------------------------------------------- */}
        {/* CHART A: TIME TREND ANALYSIS                                      */}
        {/* ----------------------------------------------------------------- */}
        <div className="glass-card rounded-3xl p-6 border border-white/5 flex flex-col space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Time Trend Analysis</h3>
            </div>

            {/* Trend Selectors */}
            {summary?.datetime_columns && summary.datetime_columns.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap text-xs">
                {/* Date Col */}
                <select
                  value={trendDateCol}
                  onChange={(e) => setTrendDateCol(e.target.value)}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  {summary.datetime_columns.map((c) => (
                    <option key={c} value={c} className="bg-slate-900">{c}</option>
                  ))}
                </select>

                {/* Metric Col */}
                {availableBusinessMetrics.length > 0 && (
                  <select
                    value={trendMetricCol}
                    onChange={(e) => setTrendMetricCol(e.target.value)}
                    className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                  >
                    {availableBusinessMetrics.map((c) => (
                      <option key={c} value={c} className="bg-slate-900">{c}</option>
                    ))}
                  </select>
                )}

                {/* Aggregation */}
                <select
                  value={trendAgg}
                  onChange={(e) => setTrendAgg(e.target.value)}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  <option value="sum" className="bg-slate-900">Sum</option>
                  <option value="mean" className="bg-slate-900">Mean</option>
                  <option value="count" className="bg-slate-900">Count</option>
                  <option value="min" className="bg-slate-900">Min</option>
                  <option value="max" className="bg-slate-900">Max</option>
                </select>

                {/* Frequency */}
                <select
                  value={trendFreq}
                  onChange={(e) => setTrendFreq(e.target.value)}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  <option value="auto" className="bg-slate-900">Auto</option>
                  <option value="day" className="bg-slate-900">Day</option>
                  <option value="week" className="bg-slate-900">Week</option>
                  <option value="month" className="bg-slate-900">Month</option>
                  <option value="quarter" className="bg-slate-900">Quarter</option>
                  <option value="year" className="bg-slate-900">Year</option>
                </select>
              </div>
            )}
          </div>

          {/* Chart Content Area */}
          <div className="flex-1 min-h-[260px] flex items-center justify-center relative">
            {(!summary?.datetime_columns || summary.datetime_columns.length === 0) ? (
              <div className="text-center p-6 space-y-2 text-slate-400">
                <Calendar className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-xs font-semibold text-slate-300">No Datetime Column Detected</p>
                <p className="text-[11px]">Upload a dataset with a date or timestamp column to unlock trend analysis.</p>
              </div>
            ) : trendError ? (
              <div className="text-center p-6 space-y-3">
                <p className="text-xs text-rose-400 font-semibold">{trendError}</p>
                <button
                  onClick={fetchTrend}
                  className="text-xs bg-white/10 hover:bg-white/15 px-3 py-1.5 rounded-lg text-white font-medium"
                >
                  Retry Trend Calculation
                </button>
              </div>
            ) : trendLoading ? (
              <div className="flex flex-col items-center gap-2 text-slate-400 text-xs">
                <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
                <span>Calculating trend...</span>
              </div>
            ) : trendData && trendData.data && trendData.data.length > 0 ? (
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="period" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip content={<CustomChartTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#818cf8"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#trendGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-xs text-slate-400">No trend data available for current selection.</p>
            )}
          </div>
        </div>

        {/* ----------------------------------------------------------------- */}
        {/* CHART B: CATEGORY COMPARISON (Top Performers)                     */}
        {/* ----------------------------------------------------------------- */}
        <div className="glass-card rounded-3xl p-6 border border-white/5 flex flex-col space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Category Performance</h3>
            </div>

            {/* Category Selectors */}
            {summary?.categorical_columns && summary.categorical_columns.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap text-xs">
                {/* Category Col */}
                <select
                  value={catCategoryCol}
                  onChange={(e) => setCatCategoryCol(e.target.value)}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  {summary.categorical_columns.map((c) => (
                    <option key={c} value={c} className="bg-slate-900">{c}</option>
                  ))}
                </select>

                {/* Metric Col */}
                {availableBusinessMetrics.length > 0 && (
                  <select
                    value={catMetricCol}
                    onChange={(e) => setCatMetricCol(e.target.value)}
                    className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                  >
                    {availableBusinessMetrics.map((c) => (
                      <option key={c} value={c} className="bg-slate-900">{c}</option>
                    ))}
                  </select>
                )}

                {/* Aggregation */}
                <select
                  value={catAgg}
                  onChange={(e) => setCatAgg(e.target.value)}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  <option value="sum" className="bg-slate-900">Sum</option>
                  <option value="mean" className="bg-slate-900">Mean</option>
                  <option value="count" className="bg-slate-900">Count</option>
                  <option value="min" className="bg-slate-900">Min</option>
                  <option value="max" className="bg-slate-900">Max</option>
                </select>

                {/* Limit */}
                <select
                  value={catLimit}
                  onChange={(e) => setCatLimit(Number(e.target.value))}
                  className="bg-black/50 border border-white/10 text-slate-300 rounded-lg px-2 py-1 focus:outline-none"
                >
                  <option value={5} className="bg-slate-900">Top 5</option>
                  <option value={10} className="bg-slate-900">Top 10</option>
                  <option value={15} className="bg-slate-900">Top 15</option>
                </select>
              </div>
            )}
          </div>

          {/* Chart Content Area */}
          <div className="flex-1 min-h-[260px] flex items-center justify-center relative">
            {(!summary?.categorical_columns || summary.categorical_columns.length === 0) ? (
              <div className="text-center p-6 space-y-2 text-slate-400">
                <Filter className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-xs font-semibold text-slate-300">No Categorical Column Detected</p>
                <p className="text-[11px]">Upload a dataset with categorical fields to unlock segment comparison.</p>
              </div>
            ) : catError ? (
              <div className="text-center p-6 space-y-3">
                <p className="text-xs text-rose-400 font-semibold">{catError}</p>
                <button
                  onClick={fetchCategoryCharts}
                  className="text-xs bg-white/10 hover:bg-white/15 px-3 py-1.5 rounded-lg text-white font-medium"
                >
                  Retry Category Comparison
                </button>
              </div>
            ) : catLoading ? (
              <div className="flex flex-col items-center gap-2 text-slate-400 text-xs">
                <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
                <span>Aggregating categories...</span>
              </div>
            ) : catData && catData.items && catData.items.length > 0 ? (
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={catData.items} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="category" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip content={<CustomChartTooltip />} />
                    <Bar dataKey="value" fill="#a855f7" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-xs text-slate-400">No category data available for current selection.</p>
            )}
          </div>
        </div>

      </div>

      {/* =================================================================== */}
      {/* 5. BOTTOM PERFORMERS WIDGET                                         */}
      {/* =================================================================== */}
      {summary?.categorical_columns && summary.categorical_columns.length > 0 && (
        <div className="glass-card rounded-3xl p-6 border border-white/5 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <ArrowDownRight className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Lowest Performers ({catCategoryCol || 'Category'} by {catMetricCol || 'Metric'})
              </h3>
            </div>
            <span className="text-[11px] text-slate-400">
              Sorted ascending &bull; Highlighting low-volume opportunities
            </span>
          </div>

          {bottomError ? (
            <p className="text-xs text-rose-400 py-3">{bottomError}</p>
          ) : bottomLoading ? (
            <div className="py-6 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
              <span>Fetching lowest performers...</span>
            </div>
          ) : bottomData && bottomData.items && bottomData.items.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {bottomData.items.map((item, idx) => (
                <div key={idx} className="bg-black/40 border border-white/5 rounded-2xl p-4 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200 truncate">{item.category}</span>
                    <span className="text-[10px] font-bold text-amber-400/90 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                      Rank #{idx + 1}
                    </span>
                  </div>
                  <div className="text-lg font-bold text-amber-400 font-mono">
                    {typeof item.value === 'number'
                      ? item.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                      : item.value}
                  </div>
                  <div className="text-[10px] text-slate-400">Aggregated {catAgg}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-3">No bottom performer items available.</p>
          )}
        </div>
      )}

      {/* =================================================================== */}
      {/* 6. INTELLIGENCE: STATISTICAL ANOMALIES & TIME-SERIES FORECASTING   */}
      {/* =================================================================== */}
      <div className="space-y-6 pt-4 border-t border-white/5">
        {/* Section Title Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg md:text-xl font-bold text-white tracking-tight flex items-center gap-2">
                Executive Intelligence & Projections
              </h2>
              <p className="text-xs text-slate-400">
                Deterministic IQR Outlier Isolation & Multi-Period Time-Series Projections
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/30">
              Data Brain Intelligence
            </span>
          </div>
        </div>

        {/* 2-Column Responsive Intelligence Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* --------------------------------------------------------------- */}
          {/* A. ANOMALY DETECTION MODULE                                     */}
          {/* --------------------------------------------------------------- */}
          <div className="glass-card rounded-3xl p-6 border border-white/5 flex flex-col space-y-5 shadow-2xl">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 pb-4">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Statistical Anomaly Detection
                </h3>
              </div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30">
                IQR Method
              </span>
            </div>

            {/* Controls Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-black/40 p-4 rounded-2xl border border-white/5">
              {/* Metric Selector */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Metric Column *</label>
                <select
                  value={anomalyMetricCol}
                  onChange={(e) => setAnomalyMetricCol(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-amber-500/50 cursor-pointer"
                >
                  {availableBusinessMetrics.map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      📊 {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Optional Date Column */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Date Column (Optional)</label>
                <select
                  value={anomalyDateCol}
                  onChange={(e) => setAnomalyDateCol(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-amber-500/50 cursor-pointer"
                >
                  <option value="" className="bg-slate-900 text-slate-400">None (Index only)</option>
                  {(summary?.datetime_columns || []).map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      📅 {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Optional Dimension Column */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Dimension Column (Optional)</label>
                <select
                  value={anomalyDimCol}
                  onChange={(e) => setAnomalyDimCol(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-amber-500/50 cursor-pointer"
                >
                  <option value="" className="bg-slate-900 text-slate-400">None (Metric only)</option>
                  {(summary?.categorical_columns || []).map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      🏷️ {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Outlier Limit */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Display Limit</label>
                <select
                  value={anomalyLimit}
                  onChange={(e) => setAnomalyLimit(Number(e.target.value))}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-amber-500/50 cursor-pointer"
                >
                  <option value={10} className="bg-slate-900">10 outliers</option>
                  <option value={20} className="bg-slate-900">20 outliers</option>
                  <option value={50} className="bg-slate-900">50 outliers</option>
                  <option value={100} className="bg-slate-900">100 outliers</option>
                </select>
              </div>

              {/* Trigger Button */}
              <div className="sm:col-span-2 pt-1">
                <button
                  type="button"
                  onClick={handleDetectAnomalies}
                  disabled={anomalyLoading || availableBusinessMetrics.length === 0}
                  className="w-full py-2.5 px-4 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-amber-600/20 active:scale-98"
                >
                  {anomalyLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Evaluating IQR Boundaries...</span>
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="w-4 h-4" />
                      <span>Detect Anomalies in {anomalyMetricCol || 'Metric'}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Content Display Area */}
            <div className="flex-1 flex flex-col justify-center min-h-[220px]">
              {anomalyError ? (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span>Anomaly Detection Error</span>
                  </div>
                  <p>{anomalyError}</p>
                  <button
                    onClick={handleDetectAnomalies}
                    className="mt-1 px-3 py-1 bg-white/10 hover:bg-white/15 rounded-lg text-white font-medium cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              ) : anomalyLoading ? (
                <div className="flex flex-col items-center justify-center gap-2 py-8 text-slate-400 text-xs">
                  <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
                  <span>Computing quartiles (Q1, Q3) and isolating outliers...</span>
                </div>
              ) : anomalyData ? (
                <div className="space-y-4">
                  {/* Summary Metric Stats */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {/* Anomaly Count */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Anomalies</span>
                      <div className="text-xl font-bold font-mono mt-0.5">
                        <span className={anomalyData.anomaly_count > 0 ? 'text-rose-400' : 'text-emerald-400'}>
                          {anomalyData.anomaly_count}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">{anomalyData.anomaly_percentage}% of total</span>
                    </div>

                    {/* Normal Bounds */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">IQR Bounds</span>
                      <div className="text-xs font-bold font-mono text-indigo-300 mt-1 truncate">
                        [{typeof anomalyData.lower_bound === 'number' ? anomalyData.lower_bound.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}{' '}
                        to{' '}
                        {typeof anomalyData.upper_bound === 'number' ? anomalyData.upper_bound.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}]
                      </div>
                      <span className="text-[10px] text-slate-400">Normal Range</span>
                    </div>

                    {/* Quartiles Q1 / Q3 */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Quartiles</span>
                      <div className="text-xs font-bold font-mono text-slate-200 mt-1">
                        Q1: {typeof anomalyData.q1 === 'number' ? anomalyData.q1.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Q3: {typeof anomalyData.q3 === 'number' ? anomalyData.q3.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}
                      </span>
                    </div>

                    {/* Normal Count */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Normal Records</span>
                      <div className="text-xl font-bold font-mono text-slate-200 mt-0.5">
                        {anomalyData.normal_count?.toLocaleString()}
                      </div>
                      <span className="text-[10px] text-slate-400">Within range</span>
                    </div>
                  </div>

                  {/* Outlier Records List */}
                  {anomalyData.anomalies && anomalyData.anomalies.length > 0 ? (
                    <div className="space-y-2">
                      <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                        <span>Flagged Outliers ({anomalyData.anomalies.length} displayed):</span>
                        <span className="text-[10px] text-slate-500 font-mono">Sorted by severity</span>
                      </div>
                      <div className="max-h-56 overflow-y-auto custom-scrollbar space-y-1.5 pr-1">
                        {anomalyData.anomalies.map((anom, idx) => {
                          const isHigh = anom.direction === 'high';
                          return (
                            <div
                              key={idx}
                              className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs hover:bg-white/5 transition-colors"
                            >
                              <div className="flex items-center gap-2">
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                                    isHigh 
                                      ? 'bg-rose-500/15 text-rose-300 border-rose-500/30' 
                                      : 'bg-blue-500/15 text-blue-300 border-blue-500/30'
                                  }`}
                                >
                                  {isHigh ? '🔺 High Outlier' : '🔻 Low Outlier'}
                                </span>

                                <span className="font-mono font-bold text-white">
                                  {typeof anom.value === 'number' 
                                    ? anom.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) 
                                    : anom.value}
                                </span>
                              </div>

                              <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                                {anom.date && (
                                  <span className="flex items-center gap-1 text-slate-300">
                                    <Calendar className="w-3 h-3 text-indigo-400" />
                                    {anom.date}
                                  </span>
                                )}
                                {(anom.category || anom.dimension) && (
                                  <span className="px-1.5 py-0.5 rounded bg-white/5 text-slate-300">
                                    {anom.category || anom.dimension}
                                  </span>
                                )}
                                {anom.row_index !== undefined && (
                                  <span className="text-slate-500">
                                    #{anom.row_index}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
                      <div>
                        <div className="font-semibold text-emerald-200">Normal Statistical Distribution</div>
                        <p className="text-slate-400 mt-0.5">
                          Zero outliers detected in '{anomalyData.column}'. All observations fall comfortably within the calculated IQR range.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 space-y-2">
                  <ShieldAlert className="w-8 h-8 mx-auto text-slate-600" />
                  <p className="text-xs font-semibold text-slate-400">No Anomaly Scan Executed</p>
                  <p className="text-[11px] max-w-xs mx-auto">
                    Select a metric column above and click "Detect Anomalies" to isolate statistical spikes and drops.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* --------------------------------------------------------------- */}
          {/* B. TIME-SERIES FORECASTING MODULE                               */}
          {/* --------------------------------------------------------------- */}
          <div className="glass-card rounded-3xl p-6 border border-white/5 flex flex-col space-y-5 shadow-2xl">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/5 pb-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Deterministic Time-Series Forecast
                </h3>
              </div>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30">
                Linear Trend Extrapolation
              </span>
            </div>

            {/* Controls Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-black/40 p-4 rounded-2xl border border-white/5">
              {/* Metric Selector */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Metric Column *</label>
                <select
                  value={forecastMetricCol}
                  onChange={(e) => setForecastMetricCol(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-purple-500/50 cursor-pointer"
                >
                  {availableBusinessMetrics.map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      📊 {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date Column */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Date Column *</label>
                <select
                  value={forecastDateCol}
                  onChange={(e) => setForecastDateCol(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-purple-500/50 cursor-pointer"
                >
                  {(summary?.datetime_columns || []).map((col) => (
                    <option key={col} value={col} className="bg-slate-900 text-white">
                      📅 {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Periods Selector (1 to 24) */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Forecast Periods</label>
                <select
                  value={forecastPeriods}
                  onChange={(e) => setForecastPeriods(Number(e.target.value))}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-purple-500/50 cursor-pointer"
                >
                  <option value={3} className="bg-slate-900">Next 3 periods</option>
                  <option value={6} className="bg-slate-900">Next 6 periods</option>
                  <option value={12} className="bg-slate-900">Next 12 periods</option>
                  <option value={24} className="bg-slate-900">Next 24 periods (Max)</option>
                </select>
              </div>

              {/* Cadence / Frequency */}
              <div>
                <label className="block text-slate-400 mb-1 font-medium">Cadence / Frequency</label>
                <select
                  value={forecastFreq}
                  onChange={(e) => setForecastFreq(e.target.value)}
                  className="w-full bg-black/60 border border-white/10 text-slate-200 rounded-xl px-3 py-2 outline-none focus:border-purple-500/50 cursor-pointer"
                >
                  <option value="auto" className="bg-slate-900">Auto-detect cadence</option>
                  <option value="month" className="bg-slate-900">Monthly (%Y-%m)</option>
                  <option value="day" className="bg-slate-900">Daily (%Y-%m-%d)</option>
                  <option value="week" className="bg-slate-900">Weekly (%Y-W%V)</option>
                  <option value="quarter" className="bg-slate-900">Quarterly (%Y-Q%q)</option>
                  <option value="year" className="bg-slate-900">Yearly (%Y)</option>
                </select>
              </div>

              {/* Trigger Button */}
              <div className="sm:col-span-2 pt-1">
                <button
                  type="button"
                  onClick={handleGenerateForecast}
                  disabled={forecastLoading || !summary?.datetime_columns || summary.datetime_columns.length === 0}
                  className="w-full py-2.5 px-4 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer shadow-lg shadow-purple-600/20 active:scale-98"
                >
                  {forecastLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Fitting Trend Regression...</span>
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4" />
                      <span>Forecast Next {forecastPeriods} Periods</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Content Display Area */}
            <div className="flex-1 flex flex-col justify-center min-h-[220px]">
              {(!summary?.datetime_columns || summary.datetime_columns.length === 0) ? (
                <div className="text-center py-8 text-slate-500 space-y-2">
                  <Calendar className="w-8 h-8 mx-auto text-slate-600" />
                  <p className="text-xs font-semibold text-slate-400">No Datetime Column Detected</p>
                  <p className="text-[11px] max-w-xs mx-auto">
                    Forecasting requires at least one date or timestamp column to perform chronological time-series regression.
                  </p>
                </div>
              ) : forecastError ? (
                <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-semibold">
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span>Forecast Calculation Error</span>
                  </div>
                  <p>{forecastError}</p>
                  <button
                    onClick={handleGenerateForecast}
                    className="mt-1 px-3 py-1 bg-white/10 hover:bg-white/15 rounded-lg text-white font-medium cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              ) : forecastLoading ? (
                <div className="flex flex-col items-center justify-center gap-2 py-8 text-slate-400 text-xs">
                  <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
                  <span>Computing historical trendline and projecting future periods...</span>
                </div>
              ) : forecastData ? (
                <div className="space-y-4">
                  {/* Disclaimer Banner (Requirement 3) */}
                  <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-500/30 text-xs text-purple-200 flex items-start gap-2.5">
                    <TrendingUp className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block text-purple-300">Statistical Projection Notice</span>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        Forecast values are statistical projections based on historical patterns. Not historical facts.
                      </p>
                    </div>
                  </div>

                  {/* Trend Metrics Bar */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    {/* Trend Direction */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Trend Direction</span>
                      <div className="text-sm font-bold font-mono mt-1 flex items-center gap-1.5">
                        {forecastData.trend_direction === 'up' ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <TrendingUp className="w-4 h-4" /> Upward
                          </span>
                        ) : forecastData.trend_direction === 'down' ? (
                          <span className="text-rose-400 flex items-center gap-1">
                            <TrendingDown className="w-4 h-4" /> Downward
                          </span>
                        ) : (
                          <span className="text-slate-400">➡️ Flat</span>
                        )}
                      </div>
                      <span className="text-[10px] text-slate-500">
                        Slope: {typeof forecastData.trend_slope === 'number' ? forecastData.trend_slope.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-'}
                      </span>
                    </div>

                    {/* Historical Observation Count */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Historical Base</span>
                      <div className="text-lg font-bold font-mono text-indigo-300 mt-0.5">
                        {forecastData.historical_count || (forecastData.historical ? forecastData.historical.length : 0)}
                      </div>
                      <span className="text-[10px] text-slate-500">observations</span>
                    </div>

                    {/* Projected Count */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Projected</span>
                      <div className="text-lg font-bold font-mono text-purple-300 mt-0.5">
                        +{forecastData.forecast_periods || (forecastData.forecast ? forecastData.forecast.length : 0)}
                      </div>
                      <span className="text-[10px] text-slate-500">future periods</span>
                    </div>

                    {/* Cadence */}
                    <div className="p-3 rounded-xl bg-black/50 border border-white/5">
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Cadence</span>
                      <div className="text-sm font-bold font-mono text-slate-200 mt-1 capitalize">
                        {forecastData.frequency || 'Monthly'}
                      </div>
                      <span className="text-[10px] text-slate-500">time bucket</span>
                    </div>
                  </div>

                  {/* Recharts Dual-Series Chart */}
                  <div className="w-full h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={combinedForecastChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis dataKey="period" stroke="#64748b" fontSize={11} />
                        <YAxis stroke="#64748b" fontSize={11} />
                        <Tooltip content={<ForecastChartTooltip />} />
                        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                        <Line
                          type="monotone"
                          dataKey="historical"
                          name="Historical Observation"
                          stroke="#6366f1"
                          strokeWidth={2.5}
                          dot={{ r: 3, fill: '#6366f1' }}
                          activeDot={{ r: 5 }}
                        />
                        <Line
                          type="monotone"
                          dataKey="forecast"
                          name="Projected Forecast"
                          stroke="#c084fc"
                          strokeWidth={2.5}
                          strokeDasharray="5 5"
                          dot={{ r: 4, stroke: '#c084fc', strokeWidth: 2, fill: '#0f172a' }}
                          activeDot={{ r: 6 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Projected Estimates Cards */}
                  {forecastData.forecast && forecastData.forecast.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[11px] font-semibold text-purple-300 block">
                        Projected Estimates ({forecastData.forecast.length} periods):
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {forecastData.forecast.map((f, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl bg-purple-950/20 border border-purple-500/20 flex flex-col space-y-0.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-slate-300">{f.period}</span>
                              <span className="text-[9px] font-bold uppercase tracking-wider text-purple-300 bg-purple-500/10 px-1.5 py-0.2 rounded border border-purple-500/30">
                                Projected
                              </span>
                            </div>
                            <span className="text-sm font-bold font-mono text-purple-200">
                              {typeof f.predicted_value === 'number'
                                ? f.predicted_value.toLocaleString(undefined, { maximumFractionDigits: 2 })
                                : f.predicted_value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 space-y-2">
                  <TrendingUp className="w-8 h-8 mx-auto text-slate-600" />
                  <p className="text-xs font-semibold text-slate-400">No Forecast Generated</p>
                  <p className="text-[11px] max-w-xs mx-auto">
                    Select a metric column and timestamp above, then click "Forecast Next Periods" to model linear trajectory.
                  </p>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

    </div>
  );
};

export default DashboardPage;

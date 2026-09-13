import axios from 'axios';

const BACKEND_URL = 'http://127.0.0.1:8000';

const extractErrorMessage = (error, defaultMsg = 'Request failed') => {
  if (error.response?.data?.error?.message) {
    return error.response.data.error.message;
  }
  if (error.response?.data?.detail) {
    return typeof error.response.data.detail === 'string'
      ? error.response.data.detail
      : JSON.stringify(error.response.data.detail);
  }
  if (error.message && error.message !== 'canceled') {
    return error.message;
  }
  return defaultMsg;
};

export const fetchDatasets = async ({ signal } = {}) => {
  try {
    const res = await axios.get(`${BACKEND_URL}/api/datasets`, { signal });
    return res.data?.datasets || [];
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    console.error('Failed to fetch datasets:', err);
    throw new Error(extractErrorMessage(err, 'Failed to fetch datasets'));
  }
};

export const fetchDatasetProfile = async (datasetId, { signal } = {}) => {
  try {
    const res = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/profile`, { signal });
    return res.data?.profile;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch dataset profile'));
  }
};

export const fetchDatasetSummary = async (datasetId, { signal } = {}) => {
  try {
    const res = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/summary`, { signal });
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch dataset summary'));
  }
};

export const fetchDatasetKPIs = async (datasetId, { signal } = {}) => {
  try {
    const res = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/kpis`, { signal });
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch dataset KPIs'));
  }
};

export const fetchDatasetStatistics = async (datasetId, column, { signal } = {}) => {
  try {
    const res = await axios.get(
      `${BACKEND_URL}/api/datasets/${datasetId}/statistics/${encodeURIComponent(column)}`,
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch column statistics'));
  }
};

export const fetchDatasetTop = async (
  datasetId,
  { category_column, metric_column, aggregation = 'sum', limit = 5 },
  { signal } = {}
) => {
  try {
    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/top`,
      { category_column, metric_column, aggregation, limit },
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch top categories'));
  }
};

export const fetchDatasetBottom = async (
  datasetId,
  { category_column, metric_column, aggregation = 'sum', limit = 5 },
  { signal } = {}
) => {
  try {
    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/bottom`,
      { category_column, metric_column, aggregation, limit },
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch bottom performers'));
  }
};

export const fetchDatasetTrend = async (
  datasetId,
  { date_column, metric_column, aggregation = 'sum', frequency = 'auto' },
  { signal } = {}
) => {
  try {
    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/trend`,
      { date_column, metric_column, aggregation, frequency },
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch time trend'));
  }
};

export const fetchDatasetAggregate = async (
  datasetId,
  { category_column, metric_column, aggregation = 'sum' },
  { signal } = {}
) => {
  try {
    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/aggregate`,
      { category_column, metric_column, aggregation },
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch aggregation'));
  }
};

export const fetchDatasetPreview = async (datasetId, limit = 20, { signal } = {}) => {
  try {
    const res = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/preview?limit=${limit}`, { signal });
    return res.data?.preview;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to fetch dataset preview'));
  }
};

export const fetchDatasetAnomalies = async (
  datasetId,
  { metric_column, date_column, dimension_column, limit = 20 },
  { signal } = {}
) => {
  try {
    const payload = { metric_column, limit: Number(limit) || 20 };
    if (date_column) payload.date_column = date_column;
    if (dimension_column) payload.dimension_column = dimension_column;

    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/anomalies`,
      payload,
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to detect anomalies'));
  }
};

export const fetchDatasetForecast = async (
  datasetId,
  { metric_column, date_column, periods = 3, frequency = null },
  { signal } = {}
) => {
  try {
    const payload = {
      metric_column,
      date_column,
      periods: Number(periods) || 3
    };
    if (frequency && frequency !== 'auto') {
      payload.frequency = frequency;
    }

    const res = await axios.post(
      `${BACKEND_URL}/api/datasets/${datasetId}/forecast`,
      payload,
      { signal }
    );
    return res.data?.result;
  } catch (err) {
    if (axios.isCancel(err) || err.name === 'CanceledError') throw err;
    throw new Error(extractErrorMessage(err, 'Failed to generate forecast'));
  }
};


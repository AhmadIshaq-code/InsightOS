import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// ==========================================
// Chat API
// ==========================================
export const askQuestion = async (message, apiKey, datasetId = null, documentId = null) => {
  try {
    const payload = {
      query: message,
      api_key: apiKey || ''
    };
    if (datasetId) payload.dataset_id = datasetId;
    if (documentId) payload.document_id = documentId;

    const response = await axios.post(`${BACKEND_URL}/api/chat`, payload);

    if (response.data.status === 'error') {
      throw new Error(response.data.message);
    }
    
    return response.data.response;
  } catch (error) {
    console.error('API Error:', error);
    throw new Error(error.response?.data?.message || error.response?.data?.detail || error.message || 'Failed to get response from AI');
  }
};

// ==========================================
// Document (PDF) APIs / Knowledge Brain
// ==========================================
export const uploadFileToBackend = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${BACKEND_URL}/api/documents/upload`, formData);
    return response.data;
  } catch (error) {
    console.error("Upload error:", error);
    throw new Error(error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to upload file');
  }
};

export const removeFileFromBackend = async (docIdOrFilename) => {
  try {
    const response = await axios.delete(`${BACKEND_URL}/api/documents/${docIdOrFilename}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to remove file');
  }
};

export const fetchFilesFromBackend = async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/documents`);
    return response.data.documents || response.data.files || [];
  } catch (error) {
    console.error("Failed to fetch files:", error);
    return [];
  }
};

export const searchDocumentsFromBackend = async (query, topK = 5, documentId = null) => {
  try {
    const payload = { query, top_k: topK };
    if (documentId) {
      payload.document_id = documentId;
    }
    const response = await axios.post(`${BACKEND_URL}/api/documents/search`, payload);
    return response.data;
  } catch (error) {
    console.error("Failed to search documents:", error);
    throw new Error(error.response?.data?.detail || error.message || 'Failed to search documents');
  }
};

// ==========================================
// Structured Dataset APIs (InsightOS Data Brain)
// ==========================================
export const uploadDatasetToBackend = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axios.post(`${BACKEND_URL}/api/datasets/upload`, formData);
    return response.data;
  } catch (error) {
    console.error("Dataset upload error:", error);
    throw new Error(error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to upload dataset');
  }
};

export const fetchDatasetsFromBackend = async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/datasets`);
    return response.data.datasets || [];
  } catch (error) {
    console.error("Failed to fetch datasets:", error);
    return [];
  }
};

export const fetchDatasetProfile = async (datasetId) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/profile`);
    return response.data.profile;
  } catch (error) {
    console.error("Failed to fetch dataset profile:", error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch dataset profile');
  }
};

export const fetchDatasetPreview = async (datasetId, limit = 20) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/preview?limit=${limit}`);
    return response.data.preview;
  } catch (error) {
    console.error("Failed to fetch dataset preview:", error);
    throw new Error(error.response?.data?.detail || 'Failed to fetch dataset preview');
  }
};

export const removeDatasetFromBackend = async (datasetId) => {
  try {
    const response = await axios.delete(`${BACKEND_URL}/api/datasets/${datasetId}`);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message || 'Failed to remove dataset');
  }
};

export const fetchDatasetSummary = async (datasetId) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/summary`);
    return response.data.result;
  } catch (error) {
    console.error("Failed to fetch dataset summary:", error);
    throw new Error(error.response?.data?.error?.message || error.response?.data?.detail || 'Failed to fetch summary');
  }
};

export const fetchDatasetKPIs = async (datasetId) => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/datasets/${datasetId}/kpis`);
    return response.data.result;
  } catch (error) {
    console.error("Failed to fetch dataset KPIs:", error);
    throw new Error(error.response?.data?.error?.message || error.response?.data?.detail || 'Failed to fetch KPIs');
  }
};

export const fetchDatasetTopCategories = async (datasetId, categoryColumn, metricColumn, limit = 5) => {
  try {
    const response = await axios.post(`${BACKEND_URL}/api/datasets/${datasetId}/top`, {
      category_column: categoryColumn,
      metric_column: metricColumn,
      aggregation: "sum",
      limit
    });
    return response.data.result;
  } catch (error) {
    console.error("Failed to fetch top categories:", error);
    throw new Error(error.response?.data?.error?.message || error.response?.data?.detail || 'Failed to fetch top categories');
  }
};


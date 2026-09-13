import React, { createContext, useState, useCallback, useEffect } from 'react';
import { fetchDatasetsFromBackend } from '../services/groqService';

export const FileContext = createContext();

export const FileProvider = ({ children }) => {
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});

  // Datasets state
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetIdState] = useState(() => {
    return localStorage.getItem('insight_selected_dataset_id') || null;
  });

  const setSelectedDatasetId = useCallback((id) => {
    setSelectedDatasetIdState(id);
    if (id) {
      localStorage.setItem('insight_selected_dataset_id', id);
    } else {
      localStorage.removeItem('insight_selected_dataset_id');
    }
  }, []);

  const loadDatasets = useCallback(async () => {
    try {
      const list = await fetchDatasetsFromBackend();
      setDatasets(list);
      return list;
    } catch (err) {
      console.error('Failed to load datasets in FileContext:', err);
      return [];
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  const setInitialFiles = useCallback((fetchedFiles) => {
    const formatted = fetchedFiles.map(f => ({
      id: f.id,
      name: f.name,
      size: f.size,
      type: f.type,
      uploadedAt: new Date(),
      status: 'ready', // Already ingested by backend
      progress: 100
    }));
    setFiles(formatted);
  }, []);

  const addFile = useCallback((file) => {
    setFiles(prev => [...prev, {
      id: Date.now(),
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date(),
      status: 'uploading',
      progress: 0
    }]);
  }, []);

  const updateFileProgress = useCallback((fileId, progress) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, progress } : f
    ));
  }, []);

  const updateFileStatus = useCallback((fileId, status) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, status } : f
    ));
  }, []);

  const deleteFile = useCallback((fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const value = {
    files,
    addFile,
    updateFileProgress,
    updateFileStatus,
    deleteFile,
    setInitialFiles,
    datasets,
    setDatasets,
    selectedDatasetId,
    setSelectedDatasetId,
    loadDatasets
  };

  return (
    <FileContext.Provider value={value}>{children}</FileContext.Provider>
  );
};


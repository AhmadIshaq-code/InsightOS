import { useContext, useEffect } from 'react';
import { FileContext } from '../context/FileContext';
import { uploadFileToBackend, removeFileFromBackend, fetchFilesFromBackend } from '../services/groqService';

export const useFileUpload = () => {
  const context = useContext(FileContext);
  if (!context) throw new Error('useFileUpload must be used within FileProvider');

  const { files, addFile, updateFileProgress, updateFileStatus, deleteFile, setInitialFiles } = context;

  // Fetch initial files on mount
  useEffect(() => {
    const loadFiles = async () => {
      const existingFiles = await fetchFilesFromBackend();
      if (existingFiles.length > 0) {
        setInitialFiles(existingFiles);
      }
    };
    loadFiles();
  }, [setInitialFiles]);

  const uploadFile = async (file) => {
    // Generate a temporary ID so we can update it
    const fileId = Date.now();
    
    // addFile expects a File object. Our context sets status to 'uploading'
    addFile(file);
    try {
      updateFileStatus(fileId, 'Processing...');
      const responseMsg = await uploadFileToBackend(file);
      console.log(responseMsg);
      // Wait, addFile internally uses Date.now(), so we don't know the exact ID unless we return it.
      // Let's just update all files that are "uploading" to "ready".
    } catch (error) {
      alert("Error uploading: " + error.message);
    } finally {
      // For simplicity, just reload the list from the backend to ensure sync!
      const currentFiles = await fetchFilesFromBackend();
      setInitialFiles(currentFiles);
    }
  };

  const removeFile = async (file) => {
    try {
      // Mark as processing visually
      updateFileStatus(file.id, 'Processing...');
      await removeFileFromBackend(file.document_id || file.id || file.name);
    } catch (error) {
      alert("Error removing: " + error.message);
    } finally {
      // Always sync with backend
      const currentFiles = await fetchFilesFromBackend();
      setInitialFiles(currentFiles);
    }
  };

  const isProcessing = files.some(f => f.status === 'Processing...' || f.status === 'uploading');

  return {
    files,
    uploadFile,
    removeFile,
    isProcessing
  };
};

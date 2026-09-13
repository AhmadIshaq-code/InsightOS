import { useContext, useCallback, useRef } from 'react';
import { ChatContext } from '../context/ChatContext';
import { APIContext } from '../context/APIContext';
import { FileContext } from '../context/FileContext';
import { askQuestion } from '../services/groqService';

export const useChat = () => {
  const context = useContext(ChatContext);
  const apiContext = useContext(APIContext);
  const fileContext = useContext(FileContext);
  const lastPromptRef = useRef(null);
  
  if (!context) throw new Error('useChat must be used within ChatProvider');
  if (!apiContext) throw new Error('useChat must be used within APIProvider');

  const sendMessage = useCallback(async (userMessage, targetDatasetId = null) => {
    if (!userMessage || !userMessage.trim()) return;

    context.setIsLoading(true);
    context.setError(null);
    lastPromptRef.current = userMessage;

    const datasetId = targetDatasetId !== undefined && targetDatasetId !== null 
      ? targetDatasetId 
      : (fileContext?.selectedDatasetId || null);

    try {
      // Add user message
      context.addMessage({
        role: 'user',
        content: userMessage,
        queryType: 'user',
        datasetId: datasetId
      });

      // Get AI response from Python backend /api/chat
      const response = await askQuestion(userMessage, apiContext.apiKey, datasetId);

      // Add AI response
      context.addMessage({
        role: 'assistant',
        content: response,
        rawResponse: response,
        queryType: response?.intent ? `${response.intent} Analyst` : 'AI Analyst',
        datasetId: datasetId
      });

    } catch (error) {
      const errMsg = error.message || 'Failed to get response from AI';
      context.setError(errMsg);
      context.addMessage({
        role: 'error',
        content: errMsg,
        failedPrompt: userMessage
      });
    } finally {
      context.setIsLoading(false);
    }
  }, [context, apiContext.apiKey, fileContext?.selectedDatasetId]);

  const retryLastMessage = useCallback(async () => {
    if (lastPromptRef.current) {
      await sendMessage(lastPromptRef.current);
    }
  }, [sendMessage]);

  return {
    ...context,
    sendMessage,
    retryLastMessage,
    selectedDatasetId: fileContext?.selectedDatasetId,
    setSelectedDatasetId: fileContext?.setSelectedDatasetId,
    datasets: fileContext?.datasets || []
  };
};

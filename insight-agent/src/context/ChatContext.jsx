import React, { createContext, useState, useCallback } from 'react';

export const ChatContext = createContext();

export const ChatProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      timestamp: new Date(),
      ...message
    }]);
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  const value = {
    messages,
    isLoading,
    setIsLoading,
    error,
    setError,
    addMessage,
    clearChat
  };

  return (
    <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
  );
};

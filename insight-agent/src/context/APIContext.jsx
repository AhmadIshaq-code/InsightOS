import React, { createContext, useState } from 'react';

export const APIContext = createContext();

export const APIProvider = ({ children }) => {
  const [apiKey, setApiKey] = useState(
    localStorage.getItem('GROQ_API_KEY') || localStorage.getItem('groq_api_key') || ''
  );

  const updateApiKey = (key) => {
    setApiKey(key);
    localStorage.setItem('GROQ_API_KEY', key);
  };

  const value = {
    apiKey,
    updateApiKey
  };

  return (
    <APIContext.Provider value={value}>{children}</APIContext.Provider>
  );
};

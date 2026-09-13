import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ChatProvider } from './context/ChatContext';
import { FileProvider } from './context/FileContext';
import { APIProvider } from './context/APIContext';

import Navigation from './components/Navigation';
import UploadPage from './pages/UploadPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <Router>
      <APIProvider>
        <FileProvider>
          <ChatProvider>
            <div className="flex h-screen bg-[#050505] text-slate-200 font-sans overflow-hidden">
              <Navigation />
              <div className="flex-1 flex flex-col min-w-0 bg-black/40 pb-14 md:pb-0">
                <Routes>
                  <Route path="/" element={<UploadPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/dashboard/:datasetId" element={<DashboardPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Routes>
              </div>
            </div>
          </ChatProvider>
        </FileProvider>
      </APIProvider>
    </Router>
  );
}

export default App;

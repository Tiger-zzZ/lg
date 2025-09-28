import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';

import Layout from '@/components/Layout';
import HomePage from '@/pages/HomePage';
import AgentPage from '@/pages/AgentPage';
import DocumentPage from '@/pages/DocumentPage';
import ChatPage from '@/pages/ChatPage';
import SearchPage from '@/pages/SearchPage';
import WorkflowPage from '@/pages/WorkflowPage';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1890ff',
          borderRadius: 8,
        },
      }}
    >
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/agents" element={<AgentPage />} />
            <Route path="/documents" element={<DocumentPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/workflow" element={<WorkflowPage />} />
          </Routes>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
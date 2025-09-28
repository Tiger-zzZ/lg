import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';

import Layout from '@/components/Layout';
import HomePage from '@/pages/HomePage';
import AgentPage from '@/pages/AgentPage';
import DocumentPage from '@/pages/DocumentPage';
import ChatPage from '@/pages/ChatPage';
import WorkflowPage from '@/pages/WorkflowPage';

// 创建Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
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
              <Route path="/workflow" element={<WorkflowPage />} />
            </Routes>
          </Layout>
        </Router>
      </ConfigProvider>
    </QueryClientProvider>
  );
};

export default App;
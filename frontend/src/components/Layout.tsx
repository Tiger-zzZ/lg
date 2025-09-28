import React from 'react';
import { Layout as AntdLayout, Menu, Typography } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  RobotOutlined,
  FileTextOutlined,
  MessageOutlined,
  PartitionOutlined,
} from '@ant-design/icons';

const { Header, Content, Footer } = AntdLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: '/agents',
      icon: <RobotOutlined />,
      label: <Link to="/agents">Agent管理</Link>,
    },
    {
      key: '/documents',
      icon: <FileTextOutlined />,
      label: <Link to="/documents">文档管理</Link>,
    },
    {
      key: '/workflow',
      icon: <PartitionOutlined />,
      label: <Link to="/workflow">工作流</Link>,
    },
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: <Link to="/chat">智能对话</Link>,
    },
  ];

  return (
    <AntdLayout className="app-layout">
      <Header className="app-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
            🚀 LG Platform
          </Title>
          <Menu
            theme="light"
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ flex: 1, justifyContent: 'center' }}
          />
        </div>
      </Header>

      <Content className="app-content">
        {children}
      </Content>

      <Footer className="app-footer">
        LG Platform ©2024 - 基于LangGraph的多Agent平台
      </Footer>
    </AntdLayout>
  );
};

export default Layout;
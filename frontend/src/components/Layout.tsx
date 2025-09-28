import React, { useState, useEffect } from 'react';
import { Layout as AntdLayout, Menu, Typography, Button, Modal, Form, Input, message, Space } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeOutlined,
  RobotOutlined,
  FileTextOutlined,
  MessageOutlined,
  SearchOutlined,
  PartitionOutlined,
  LoginOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons';

const { Header, Content, Footer } = AntdLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loginModalVisible, setLoginModalVisible] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    // 检查本地存储中的token
    const token = localStorage.getItem('token');
    const storedUsername = localStorage.getItem('username');
    if (token && storedUsername) {
      setIsLoggedIn(true);
      setUsername(storedUsername);
    }
  }, []);

  const handleLogin = async (values: { username: string; password: string }) => {
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        const result = await response.json();
        localStorage.setItem('token', result.access_token);
        localStorage.setItem('username', values.username);
        setIsLoggedIn(true);
        setUsername(values.username);
        setLoginModalVisible(false);
        form.resetFields();
        message.success('登录成功！');
      } else {
        const error = await response.json();
        message.error(error.detail || '登录失败');
      }
    } catch (error) {
      message.error('网络错误，请稍后重试');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    setIsLoggedIn(false);
    setUsername(null);
    message.success('已退出登录');
  };

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
      key: '/search',
      icon: <SearchOutlined />,
      label: <Link to="/search">智能搜索</Link>,
    },
    {
      key: '/chat',
      icon: <MessageOutlined />,
      label: <Link to="/chat">智能对话</Link>,
    },
    {
      key: '/workflow',
      icon: <PartitionOutlined />,
      label: <Link to="/workflow">工作流</Link>,
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
          <div>
            {isLoggedIn ? (
              <Space>
                <span style={{ color: '#666' }}>
                  <UserOutlined /> {username}
                </span>
                <Button
                  type="text"
                  icon={<LogoutOutlined />}
                  onClick={handleLogout}
                >
                  退出
                </Button>
              </Space>
            ) : (
              <Button
                type="primary"
                icon={<LoginOutlined />}
                onClick={() => setLoginModalVisible(true)}
              >
                登录
              </Button>
            )}
          </div>
        </div>
      </Header>

      <Content className="app-content">
        {children}
      </Content>

      <Footer className="app-footer">
        LG Platform ©2024 - 基于LangGraph的多Agent平台
      </Footer>

      {/* 登录模态框 */}
      <Modal
        title="登录"
        open={loginModalVisible}
        onCancel={() => {
          setLoginModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleLogin}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="请输入用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setLoginModalVisible(false);
                form.resetFields();
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                登录
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </AntdLayout>
  );
};

export default Layout;
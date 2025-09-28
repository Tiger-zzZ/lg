import React from 'react';
import { Card, Row, Col, Statistic, Button, Typography, Space } from 'antd';
import {
  RobotOutlined,
  FileTextOutlined,
  MessageOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';

const { Title, Paragraph } = Typography;

const HomePage: React.FC = () => {
  return (
    <div>
      {/* 欢迎区域 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 24]} align="middle">
          <Col xs={24} md={16}>
            <Title level={1} style={{ marginBottom: 16 }}>
              🚀 欢迎使用 LG Platform
            </Title>
            <Paragraph style={{ fontSize: 16, marginBottom: 24 }}>
              基于LangGraph的多Agent平台，支持RAG（检索增强生成），
              提供智能文档处理、多Agent协作和实时对话功能。
            </Paragraph>
            <Space size="large">
              <Button type="primary" size="large" icon={<RobotOutlined />}>
                <Link to="/agents">开始使用Agent</Link>
              </Button>
              <Button size="large" icon={<MessageOutlined />}>
                <Link to="/chat">智能对话</Link>
              </Button>
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ textAlign: 'center', fontSize: 64 }}>
              🤖
            </div>
          </Col>
        </Row>
      </Card>

      {/* 统计数据 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="活跃Agent"
              value={0}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="处理文档"
              value={0}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="对话会话"
              value={0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card>
            <Statistic
              title="任务执行"
              value={0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#fa541c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 功能介绍 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} md={8}>
          <Card
            title="🤖 智能Agent"
            actions={[
              <Link key="manage" to="/agents">
                管理Agent
              </Link>,
            ]}
          >
            <Paragraph>
              支持多种类型的智能Agent，包括研究、编程、写作等，
              基于LangGraph构建强大的工作流引擎。
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            title="📚 RAG系统"
            actions={[
              <Link key="documents" to="/documents">
                文档管理
              </Link>,
            ]}
          >
            <Paragraph>
              智能文档处理和向量化存储，支持语义搜索和
              检索增强生成，提供精准的知识问答。
            </Paragraph>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card
            title="💬 实时对话"
            actions={[
              <Link key="chat" to="/chat">
                开始对话
              </Link>,
            ]}
          >
            <Paragraph>
              与Agent进行实时对话，支持多会话管理、
              上下文理解和对话历史保存。
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HomePage;
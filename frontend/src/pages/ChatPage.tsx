import React, { useState } from 'react';
import { Card, Input, Button, List, Typography, Space } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import MarkdownRenderer from '../components/MarkdownRenderer';

const { Title } = Typography;
const { Search } = Input;

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSend = async (message: string) => {
    if (!message.trim()) return;

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    try {
      // 构建对话历史
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      }));

      // 调用聊天API
      const response = await fetch('/api/v1/chat/test/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          conversation_history: conversationHistory,
          agent_type: 'chat'
        }),
      });

      if (response.ok) {
        const result = await response.json();

        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: result.message,
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);
      } else {
        const error = await response.json();

        const errorMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `抱歉，出现了错误：${error.detail || '请稍后重试'}`,
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('发送消息失败:', error);

      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '网络错误，请检查连接后重试',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={2} style={{ marginBottom: 24 }}>
        💬 智能对话
      </Title>

      <Card style={{ height: 'calc(100vh - 300px)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
          <List
            dataSource={messages}
            renderItem={(message) => (
              <List.Item
                style={{
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  border: 'none',
                  padding: '8px 0',
                }}
              >
                <div
                  style={{
                    maxWidth: '70%',
                    padding: '12px 16px',
                    borderRadius: 8,
                    backgroundColor: message.role === 'user' ? '#1890ff' : '#f0f0f0',
                    color: message.role === 'user' ? 'white' : 'black',
                  }}
                >
                  {message.role === 'assistant' ? (
                    <MarkdownRenderer
                      content={message.content}
                      className={message.role === 'user' ? 'user-message' : 'assistant-message'}
                    />
                  ) : (
                    <div>{message.content}</div>
                  )}
                  <div
                    style={{
                      fontSize: 12,
                      opacity: 0.7,
                      marginTop: 4,
                      textAlign: 'right',
                    }}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </div>
                </div>
              </List.Item>
            )}
          />

          {loading && (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Space>
                <span>🤖</span>
                <span>AI正在思考...</span>
              </Space>
            </div>
          )}

          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: 64, color: '#999' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>💭</div>
              <div>开始与AI对话吧！</div>
            </div>
          )}
        </div>

        <div>
          <Search
            placeholder="输入您的问题..."
            enterButton={<SendOutlined />}
            size="large"
            onSearch={handleSend}
            loading={loading}
          />
        </div>
      </Card>
    </div>
  );
};

export default ChatPage;
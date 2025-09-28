import React, { useState, useRef, useEffect } from 'react';
import { Card, Button, Empty, Typography, Upload, message, Progress, List, Space, Tag, Input, Divider, Spin, Modal, Descriptions } from 'antd';
import { UploadOutlined, FileTextOutlined, DeleteOutlined, EyeOutlined, QuestionCircleOutlined, SendOutlined } from '@ant-design/icons';
import MarkdownRenderer from '../components/MarkdownRenderer';

const { Title, Paragraph } = Typography;
const { Dragger } = Upload;
const { Search } = Input;

interface Document {
  document_id: string;
  file_name: string;
  created_at: string;
  chunks_count: number;
  processing_status?: string;
  file_size?: number;
}

interface QAMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

const DocumentPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [qaMessages, setQaMessages] = useState<QAMessage[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  // 加载文档列表
  const loadDocuments = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('请先登录');
        return;
      }

      const response = await fetch('/api/v1/documents/list', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const documentsData = await response.json();
        setDocuments(documentsData);
      } else {
        console.error('获取文档列表失败');
      }
    } catch (error) {
      console.error('加载文档列表失败:', error);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录后再上传文档');
        return;
      }

      const response = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (response.ok) {
        const result = await response.json();
        message.success(`文档上传成功！处理了 ${result.chunks_count} 个文档块`);

        // 添加到文档列表
        const newDocument: Document = {
          document_id: result.document_id,
          file_name: result.file_name,
          created_at: new Date().toISOString(),
          chunks_count: result.chunks_count,
        };

        setDocuments([newDocument, ...documents]);
        loadDocuments(); // 重新加载文档列表
      } else {
        const error = await response.json();
        message.error(error.detail || '文档上传失败');
      }
    } catch (error) {
      console.error('上传失败:', error);
      message.error('网络错误，请稍后重试');
    } finally {
      setUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDrop = (file: File) => {
    handleFileUpload(file);
    return false; // 阻止默认上传行为
  };

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.docx,.txt,.md',
    beforeUpload: handleDrop,
    showUploadList: false,
  };

  const handleViewDocument = (doc: Document) => {
    Modal.info({
      title: `查看文档 - ${doc.file_name}`,
      content: (
        <div>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="文件名">{doc.file_name}</Descriptions.Item>
            <Descriptions.Item label="文档ID">{doc.document_id}</Descriptions.Item>
            <Descriptions.Item label="上传时间">{new Date(doc.created_at).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="文档块数">{doc.chunks_count}</Descriptions.Item>
            <Descriptions.Item label="处理状态">
              <Tag color={doc.processing_status === 'completed' ? 'green' : 'blue'}>
                {doc.processing_status === 'completed' ? '已完成' : '处理中'}
              </Tag>
            </Descriptions.Item>
            {doc.file_size && (
              <Descriptions.Item label="文件大小">
                {(doc.file_size / 1024).toFixed(2)} KB
              </Descriptions.Item>
            )}
          </Descriptions>
        </div>
      ),
      width: 600,
    });
  };

  const handleDeleteDocument = async (documentId: string) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/documents/delete/${documentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        message.success('文档删除成功');
        loadDocuments(); // 重新加载文档列表
      } else {
        message.error('文档删除失败');
      }
    } catch (error) {
      message.error('网络错误，请稍后重试');
    }
  };

  const handleAskQuestion = async (question: string) => {
    if (!question.trim()) return;

    // 添加用户问题
    const userMessage: QAMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    setQaMessages(prev => [...prev, userMessage]);
    setQaLoading(true);

    try {
      // 构建对话历史
      const conversationHistory = qaMessages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      }));

      const token = localStorage.getItem('token');
      if (!token) {
        const errorMessage: QAMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '请先登录后再使用问答功能',
          timestamp: new Date(),
        };
        setQaMessages(prev => [...prev, errorMessage]);
        setQaLoading(false);
        return;
      }

      // 调用文档问答API
      const response = await fetch('/api/v1/chat/qa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          question: question,
          conversation_history: conversationHistory
        }),
      });

      if (response.ok) {
        const result = await response.json();

        const assistantMessage: QAMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: result.message,
          timestamp: new Date(),
        };

        setQaMessages(prev => [...prev, assistantMessage]);
      } else {
        const error = await response.json();

        const errorMessage: QAMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `抱歉，出现了错误：${error.detail || '请稍后重试'}`,
          timestamp: new Date(),
        };

        setQaMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('问答失败:', error);

      const errorMessage: QAMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '网络错误，请检查连接后重试',
        timestamp: new Date(),
      };

      setQaMessages(prev => [...prev, errorMessage]);
    } finally {
      setQaLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          📚 文档管理
        </Title>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={handleUploadClick}
          loading={uploading}
        >
          上传文档
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
      </div>

      <Card title="文档上传" style={{ marginBottom: 24 }}>
        {uploading && (
          <div style={{ marginBottom: 16 }}>
            <Progress percent={uploadProgress} status="active" />
          </div>
        )}
        <Dragger {...uploadProps} disabled={uploading}>
          <p style={{ fontSize: 48 }}>📁</p>
          <p>点击或拖拽文件到此区域上传</p>
          <p style={{ color: '#999' }}>
            支持 PDF, DOCX, TXT, MD 格式文件，最大 10MB
          </p>
        </Dragger>
      </Card>

      <Card title="我的文档">
        {documents.length === 0 ? (
          <Empty
            description="暂无文档，上传第一个文档开始使用RAG功能"
          />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={documents}
            renderItem={(doc) => (
              <List.Item
                actions={[
                  <Button
                    key="view"
                    type="link"
                    icon={<EyeOutlined />}
                    size="small"
                    onClick={() => handleViewDocument(doc)}
                  >
                    查看
                  </Button>,
                  <Button
                    key="delete"
                    type="link"
                    danger
                    icon={<DeleteOutlined />}
                    size="small"
                    onClick={() => handleDeleteDocument(doc.document_id)}
                  >
                    删除
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  avatar={<FileTextOutlined style={{ fontSize: 24 }} />}
                  title={doc.file_name}
                  description={
                    <Space>
                      <span>上传时间: {new Date(doc.created_at).toLocaleString()}</span>
                      <Tag color="blue">{doc.chunks_count} 个文档块</Tag>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 文档问答部分 */}
      <Card
        title={
          <Space>
            <QuestionCircleOutlined />
            <span>文档问答</span>
          </Space>
        }
        style={{ marginTop: 24 }}
      >
        {documents.length === 0 ? (
          <Empty
            description="请先上传文档才能进行问答"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <>
            {/* 问答历史 */}
            <div style={{ maxHeight: 400, overflowY: 'auto', marginBottom: 16 }}>
              {qaMessages.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                  <div style={{ fontSize: 48, marginBottom: 16 }}>💭</div>
                  <div>向您的文档提问吧！我会基于文档内容来回答问题</div>
                </div>
              ) : (
                <List
                  dataSource={qaMessages}
                  renderItem={(msg) => (
                    <List.Item
                      style={{
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        border: 'none',
                        padding: '8px 0',
                      }}
                    >
                      <div
                        style={{
                          maxWidth: '80%',
                          padding: '12px 16px',
                          borderRadius: 8,
                          backgroundColor: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                          color: msg.role === 'user' ? 'white' : 'black',
                        }}
                      >
                        {msg.role === 'assistant' ? (
                          <MarkdownRenderer
                            content={msg.content}
                            className={msg.role === 'user' ? 'user-message' : 'assistant-message'}
                          />
                        ) : (
                          <Paragraph style={{ margin: 0, color: 'inherit' }}>
                            {msg.content}
                          </Paragraph>
                        )}
                        <div
                          style={{
                            fontSize: 12,
                            opacity: 0.7,
                            marginTop: 4,
                            textAlign: 'right',
                          }}
                        >
                          {msg.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              )}

              {qaLoading && (
                <div style={{ textAlign: 'center', padding: 16 }}>
                  <Space>
                    <Spin />
                    <span>AI正在基于文档内容分析...</span>
                  </Space>
                </div>
              )}
            </div>

            <Divider />

            {/* 问题输入框 */}
            <Search
              placeholder="向文档提问，例如：这个文档的主要内容是什么？"
              enterButton={<Button type="primary" icon={<SendOutlined />}>提问</Button>}
              size="large"
              onSearch={handleAskQuestion}
              loading={qaLoading}
            />

            <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
              💡 提示：我会基于您上传的文档内容来回答问题，支持多轮对话
            </div>
          </>
        )}
      </Card>
    </div>
  );
};

export default DocumentPage;
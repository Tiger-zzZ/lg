import React, { useState } from 'react';
import { Card, Input, Button, List, Typography, Space, Tag, Spin, Empty, Divider } from 'antd';
import { SearchOutlined, FileTextOutlined, ClockCircleOutlined } from '@ant-design/icons';
import MarkdownRenderer from '../components/MarkdownRenderer';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

interface SearchResult {
  document_id: string;
  chunk_index: number;
  score: number;
  content_preview: string;
}

interface SearchResponse {
  message: string;
  agent_type: string;
  response_time: number;
  metadata?: {
    search_results?: SearchResult[];
    results_count?: number;
  };
}

const SearchPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [query, setQuery] = useState('');

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setQuery(searchQuery);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setSearchResults({
          message: '请先登录后再使用搜索功能',
          agent_type: 'search',
          response_time: 0,
        });
        setLoading(false);
        return;
      }

      const response = await fetch('/api/v1/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: searchQuery,
          agent_type: 'search'
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setSearchResults(result);
      } else {
        const error = await response.json();
        setSearchResults({
          message: `搜索失败：${error.detail || '请稍后重试'}`,
          agent_type: 'search',
          response_time: 0,
        });
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setSearchResults({
        message: '网络错误，请检查连接后重试',
        agent_type: 'search',
        response_time: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClearResults = () => {
    setSearchResults(null);
    setQuery('');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          🔍 智能搜索
        </Title>
        {searchResults && (
          <Button onClick={handleClearResults}>
            清除结果
          </Button>
        )}
      </div>

      {/* 搜索框 */}
      <Card style={{ marginBottom: 24 }}>
        <Search
          placeholder="输入您要搜索的内容..."
          size="large"
          enterButton={
            <Button type="primary" icon={<SearchOutlined />} loading={loading}>
              搜索
            </Button>
          }
          onSearch={handleSearch}
          loading={loading}
        />
        <div style={{ marginTop: 12, color: '#666', fontSize: 14 }}>
          💡 提示：支持关键词搜索和语义搜索，会在您上传的文档中查找相关内容
        </div>
      </Card>

      {/* 搜索结果 */}
      {loading && (
        <Card>
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>正在搜索相关文档...</div>
          </div>
        </Card>
      )}

      {searchResults && !loading && (
        <Card title={`搜索结果 - "${query}"`}>
          {/* 搜索统计信息 */}
          <div style={{ marginBottom: 16 }}>
            <Space>
              <Tag icon={<ClockCircleOutlined />} color="blue">
                耗时 {searchResults.response_time.toFixed(2)} 秒
              </Tag>
              {searchResults.metadata?.results_count !== undefined && (
                <Tag color="green">
                  找到 {searchResults.metadata.results_count} 个结果
                </Tag>
              )}
            </Space>
          </div>

          <Divider />

          {/* AI 总结 */}
          <div style={{ marginBottom: 24 }}>
            <Title level={4}>📋 智能总结</Title>
            <Card size="small" style={{ backgroundColor: '#f8f9fa' }}>
              <MarkdownRenderer content={searchResults.message} />
            </Card>
          </div>

          {/* 详细搜索结果 */}
          {searchResults.metadata?.search_results && searchResults.metadata.search_results.length > 0 && (
            <div>
              <Title level={4}>📄 相关文档片段</Title>
              <List
                itemLayout="vertical"
                dataSource={searchResults.metadata.search_results}
                renderItem={(item, index) => (
                  <List.Item
                    key={`${item.document_id}-${item.chunk_index}`}
                    style={{
                      border: '1px solid #f0f0f0',
                      borderRadius: 8,
                      padding: 16,
                      marginBottom: 12,
                    }}
                  >
                    <List.Item.Meta
                      avatar={<FileTextOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                      title={
                        <Space>
                          <span>文档片段 {index + 1}</span>
                          <Tag color="purple">
                            相似度: {(item.score * 100).toFixed(1)}%
                          </Tag>
                        </Space>
                      }
                      description={
                        <div style={{ marginTop: 8 }}>
                          <Text>{item.content_preview}</Text>
                          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                            文档ID: {item.document_id} | 块索引: {item.chunk_index}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </div>
          )}

          {searchResults.metadata?.results_count === 0 && (
            <Empty
              description="未找到相关内容"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <div>
                <p>建议：</p>
                <ul style={{ textAlign: 'left', display: 'inline-block' }}>
                  <li>尝试使用不同的关键词</li>
                  <li>检查是否已上传相关文档</li>
                  <li>使用更通用的搜索词</li>
                </ul>
              </div>
            </Empty>
          )}
        </Card>
      )}

      {/* 无结果时的状态 */}
      {!searchResults && !loading && (
        <Card>
          <Empty
            description="开始您的搜索吧！"
            image={<div style={{ fontSize: 48 }}>🔍</div>}
          >
            <div style={{ color: '#666' }}>
              在上方输入关键词，搜索您上传的文档内容
            </div>
          </Empty>
        </Card>
      )}
    </div>
  );
};

export default SearchPage;
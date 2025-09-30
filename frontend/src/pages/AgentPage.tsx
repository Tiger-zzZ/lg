import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Empty,
  Typography,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Table,
  Tag,
  Drawer,
  Descriptions,
  Switch,
  Popconfirm,
  JsonInput,
  Statistic,
  Alert,
  Tooltip
} from 'antd';
import {
  PlusOutlined,
  RobotOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  HistoryOutlined,
  EyeOutlined,
  CopyOutlined,
  DownloadOutlined,
  ReloadOutlined,
  SearchOutlined
} from '@ant-design/icons';
import MarkdownRenderer from '../components/MarkdownRenderer';
import AgentExecutionDialog from '../components/AgentExecutionDialog';
import AgentConfigForm from '../components/AgentConfigForm';
import { AGENT_TYPE_INFO, getAgentTypes } from '../constants/agentTypes';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface Agent {
  id: string;
  name: string;
  description?: string;
  type: string;
  config?: any;
  is_active: boolean;
  status: string;
  created_at: string;
  updated_at?: string;
  last_used_at?: string;
  // 统计字段
  execution_count?: number;
  success_rate?: number;
  avg_duration?: number;
  last_execution?: {
    id: string;
    status: string;
    started_at?: string;
    error_message?: string;
  };
}

interface AgentExecution {
  id: string;
  agent_id: string;
  input_data: any;
  output_data?: any;
  status: string;
  error_message?: string;
  duration_ms?: string;
  started_at: string;
  completed_at?: string;
}

const AgentPage: React.FC = () => {
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [configDrawerVisible, setConfigDrawerVisible] = useState(false);
  const [historyDrawerVisible, setHistoryDrawerVisible] = useState(false);
  const [executionDialogVisible, setExecutionDialogVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [filteredExecutions, setFilteredExecutions] = useState<AgentExecution[]>([]);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [form] = Form.useForm();
  const [selectedType, setSelectedType] = useState<string>('');

  // 加载agents列表
  const loadAgents = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch('/api/v1/agents/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const agentList = await response.json();
        setAgents(agentList);
      } else {
        message.error('获取Agent列表失败');
      }
    } catch (error) {
      console.error('加载Agents失败:', error);
      message.error('网络错误，请稍后重试');
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const handleCreateAgent = async (values: any) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        setLoading(false);
        return;
      }

      const response = await fetch('/api/v1/agents/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: values.name,
          type: values.type,
          description: values.description,
          config: {}
        }),
      });

      if (response.ok) {
        const newAgent = await response.json();
        message.success('Agent创建成功！');
        setCreateModalVisible(false);
        form.resetFields();
        loadAgents(); // 重新加载列表
      } else {
        const error = await response.json();
        message.error(error.detail || 'Agent创建失败');
      }
    } catch (error) {
      console.error('创建Agent失败:', error);
      message.error('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteAgent = async (agent: Agent) => {
    setSelectedAgent(agent);
    setExecutionDialogVisible(true);
  };

  // 执行Agent的实际逻辑
  const executeAgent = async (input: string, continueConversation?: boolean) => {
    if (!selectedAgent) {
      throw new Error('未选择Agent');
    }

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('请先登录');
      }

      const response = await fetch(`/api/v1/agents/${selectedAgent.id}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          messages: [input],
          metadata: { continueConversation }
        }),
      });

      if (response.ok) {
        const result = await response.json();

        // 更新agents状态
        loadAgents();

        return {
          status: result.status || 'completed',
          result: result.result || '',
          duration: result.duration,
          error: result.error
        };
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Agent执行失败');
      }
    } catch (error: any) {
      console.error('执行Agent失败:', error);
      throw error;
    }
  };

  const handleToggleAgent = async (agent: Agent) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/agents/${agent.id}/toggle`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        message.success(`Agent已${agent.is_active ? '禁用' : '启用'}`);
        loadAgents();
      } else {
        const error = await response.json();
        message.error(error.detail || '操作失败');
      }
    } catch (error) {
      console.error('切换Agent状态失败:', error);
      message.error('网络错误，请稍后重试');
    }
  };

  const handleDeleteAgent = async (agent: Agent) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/agents/${agent.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        message.success('Agent删除成功');
        loadAgents();
      } else {
        const error = await response.json();
        message.error(error.detail || '删除失败');
      }
    } catch (error) {
      console.error('删除Agent失败:', error);
      message.error('网络错误，请稍后重试');
    }
  };

  const handleConfigAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    setConfigDrawerVisible(true);
  };

  const handleSaveConfig = async (config: Record<string, any>) => {
    if (!selectedAgent) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        setLoading(false);
        return;
      }

      const response = await fetch(`/api/v1/agents/${selectedAgent.id}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ config }),
      });

      if (response.ok) {
        message.success('配置更新成功');
        setConfigDrawerVisible(false);
        loadAgents();
      } else {
        const error = await response.json();
        message.error(error.detail || '配置更新失败');
      }
    } catch (error) {
      message.error('网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const handleViewHistory = async (agent: Agent) => {
    setSelectedAgent(agent);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/agents/${agent.id}/executions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const executionList = await response.json();
        setExecutions(executionList);
        setFilteredExecutions(executionList);
        setSearchText('');
        setStatusFilter('all');
        setHistoryDrawerVisible(true);
      } else {
        message.error('加载执行历史失败');
      }
    } catch (error) {
      console.error('加载执行历史失败:', error);
      message.error('网络错误，请稍后重试');
    }
  };

  // 筛选执行历史
  const filterExecutions = (search: string, status: string) => {
    let filtered = executions;

    // 状态筛选
    if (status !== 'all') {
      filtered = filtered.filter(e => e.status === status);
    }

    // 搜索筛选
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(e => {
        const inputStr = JSON.stringify(e.input_data).toLowerCase();
        const outputStr = JSON.stringify(e.output_data).toLowerCase();
        return inputStr.includes(searchLower) || outputStr.includes(searchLower);
      });
    }

    setFilteredExecutions(filtered);
  };

  // 处理搜索
  const handleSearch = (value: string) => {
    setSearchText(value);
    filterExecutions(value, statusFilter);
  };

  // 处理状态筛选
  const handleStatusFilter = (value: string) => {
    setStatusFilter(value);
    filterExecutions(searchText, value);
  };

  // 重试执行
  const handleRetryExecution = async (execution: AgentExecution) => {
    if (!selectedAgent) return;

    try {
      const input = execution.input_data?.messages?.[0] || '';
      setSelectedAgent(selectedAgent);
      setExecutionDialogVisible(true);
      setHistoryDrawerVisible(false);
    } catch (error) {
      console.error('重试失败:', error);
      message.error('重试失败');
    }
  };

  // 复制执行结果
  const handleCopyExecution = (execution: AgentExecution) => {
    const content = execution.output_data?.result || JSON.stringify(execution.output_data, null, 2);
    navigator.clipboard.writeText(content);
    message.success('已复制到剪贴板');
  };

  // 导出执行结果
  const handleExportExecution = (execution: AgentExecution) => {
    const content = execution.output_data?.result || JSON.stringify(execution.output_data, null, 2);
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-${execution.id}-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    message.success('导出成功');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'idle': return 'green';
      case 'running': return 'blue';
      case 'error': return 'red';
      case 'disabled': return 'gray';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'idle': return '空闲';
      case 'running': return '运行中';
      case 'error': return '错误';
      case 'disabled': return '已禁用';
      default: return status;
    }
  };

  const executionColumns = [
    {
      title: '执行时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'completed' ? 'green' : status === 'failed' ? 'red' : 'blue'}>
          {status === 'completed' ? '完成' : status === 'failed' ? '失败' : '运行中'}
        </Tag>
      ),
    },
    {
      title: '执行时长',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      render: (duration: string) => duration ? `${duration}ms` : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record: AgentExecution) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                Modal.info({
                  title: '执行详情',
                  content: (
                    <div>
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="输入">
                          <pre style={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(record.input_data, null, 2)}
                          </pre>
                        </Descriptions.Item>
                        {record.output_data && (
                          <Descriptions.Item label="输出">
                            {record.output_data.result ? (
                              <div style={{ border: '1px solid #f0f0f0', padding: '12px', borderRadius: '6px', maxHeight: '300px', overflow: 'auto' }}>
                                <MarkdownRenderer content={record.output_data.result} />
                              </div>
                            ) : (
                              <pre style={{ whiteSpace: 'pre-wrap' }}>
                                {JSON.stringify(record.output_data, null, 2)}
                              </pre>
                            )}
                          </Descriptions.Item>
                        )}
                        {record.error_message && (
                          <Descriptions.Item label="错误信息">
                            <Text type="danger">{record.error_message}</Text>
                          </Descriptions.Item>
                        )}
                      </Descriptions>
                    </div>
                  ),
                  width: 900,
                });
              }}
            />
          </Tooltip>
          <Tooltip title="重试">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleRetryExecution(record)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopyExecution(record)}
            />
          </Tooltip>
          <Tooltip title="导出">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleExportExecution(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          🤖 Agent管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          创建Agent
        </Button>
      </div>

      {agents.length === 0 ? (
        <Card>
          <Empty
            description="暂无Agent，点击上方按钮创建第一个Agent"
          />
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: 16 }}>
          {agents.map((agent) => (
            <Card
              key={agent.id}
              title={
                <Space>
                  <RobotOutlined />
                  {agent.name}
                  <Tag color={getStatusColor(agent.status)}>
                    {getStatusText(agent.status)}
                  </Tag>
                </Space>
              }
              extra={
                <Switch
                  checked={agent.is_active}
                  onChange={() => handleToggleAgent(agent)}
                  size="small"
                />
              }
            >
              <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
                <Descriptions.Item label="类型">{agent.type}</Descriptions.Item>
                <Descriptions.Item label="描述">{agent.description || '暂无描述'}</Descriptions.Item>
              </Descriptions>

              {/* 统计信息 */}
              {(agent.execution_count !== undefined && agent.execution_count > 0) && (
                <div style={{ marginBottom: 16, padding: 12, background: '#fafafa', borderRadius: 4 }}>
                  <Statistic.Group size="small">
                    <Statistic
                      title="执行次数"
                      value={agent.execution_count}
                      valueStyle={{ fontSize: 18 }}
                    />
                    <Statistic
                      title="成功率"
                      value={agent.success_rate || 0}
                      suffix="%"
                      precision={1}
                      valueStyle={{
                        fontSize: 18,
                        color: (agent.success_rate || 0) >= 80 ? '#52c41a' : (agent.success_rate || 0) >= 50 ? '#fa8c16' : '#f5222d'
                      }}
                    />
                    <Statistic
                      title="平均时长"
                      value={agent.avg_duration || 0}
                      suffix="ms"
                      precision={0}
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Statistic.Group>
                </div>
              )}

              {/* 最近执行 */}
              {agent.last_execution && (
                <Alert
                  message={`最后执行于 ${new Date(agent.last_execution.started_at || '').toLocaleString()}`}
                  description={agent.last_execution.error_message}
                  type={agent.last_execution.status === 'completed' ? 'success' : 'error'}
                  showIcon
                  style={{ marginBottom: 12, fontSize: 12 }}
                />
              )}

              <p style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>
                <strong>创建时间:</strong> {new Date(agent.created_at).toLocaleString()}
              </p>

              <Space style={{ marginTop: 12, width: '100%' }} direction="vertical">
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Button
                    size="small"
                    icon={<SettingOutlined />}
                    onClick={() => handleConfigAgent(agent)}
                  >
                    配置
                  </Button>
                  <Button
                    size="small"
                    icon={<HistoryOutlined />}
                    onClick={() => handleViewHistory(agent)}
                  >
                    历史
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    disabled={!agent.is_active || agent.status === 'running'}
                    onClick={() => handleExecuteAgent(agent)}
                  >
                    执行
                  </Button>
                  <Popconfirm
                    title="确定要删除这个Agent吗？"
                    onConfirm={() => handleDeleteAgent(agent)}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                    >
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              </Space>
            </Card>
          ))}
        </div>
      )}

      {/* 创建Agent Modal */}
      <Modal
        title="创建新Agent"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          setSelectedType('');
          form.resetFields();
        }}
        footer={null}
        width={800}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateAgent}
        >
          <Form.Item
            name="name"
            label="Agent名称"
            rules={[{ required: true, message: '请输入Agent名称' }]}
          >
            <Input placeholder="请输入Agent名称" />
          </Form.Item>

          <Form.Item
            name="type"
            label="选择Agent类型"
            rules={[{ required: true, message: '请选择Agent类型' }]}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
              {getAgentTypes().map((type) => {
                const typeInfo = AGENT_TYPE_INFO[type];
                const IconComponent = typeInfo.icon as any;
                const isSelected = selectedType === type;

                return (
                  <Card
                    key={type}
                    hoverable
                    style={{
                      border: isSelected ? `2px solid ${typeInfo.color}` : '1px solid #d9d9d9',
                      cursor: 'pointer',
                      transition: 'all 0.3s'
                    }}
                    onClick={() => {
                      setSelectedType(type);
                      form.setFieldValue('type', type);
                    }}
                    bodyStyle={{ padding: 16 }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                      <div
                        style={{
                          fontSize: 32,
                          color: typeInfo.color,
                          display: 'flex',
                          alignItems: 'center'
                        }}
                      >
                        <IconComponent />
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 8 }}>
                          {typeInfo.name}
                        </div>
                        <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                          {typeInfo.description}
                        </div>
                        <Space size={[4, 4]} wrap style={{ marginBottom: 8 }}>
                          {typeInfo.capabilities.slice(0, 3).map((cap, index) => (
                            <Tag key={index} color={typeInfo.color} style={{ fontSize: 11, margin: 0 }}>
                              {cap}
                            </Tag>
                          ))}
                          {typeInfo.capabilities.length > 3 && (
                            <Tag color="default" style={{ fontSize: 11, margin: 0 }}>
                              +{typeInfo.capabilities.length - 3}
                            </Tag>
                          )}
                        </Space>
                        <div style={{ fontSize: 11, color: '#999', fontStyle: 'italic' }}>
                          💡 {typeInfo.usageExample.substring(0, 40)}...
                        </div>
                      </div>
                    </div>
                    {isSelected && (
                      <div
                        style={{
                          position: 'absolute',
                          top: 8,
                          right: 8,
                          width: 24,
                          height: 24,
                          borderRadius: '50%',
                          backgroundColor: typeInfo.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'white',
                          fontSize: 12
                        }}
                      >
                        ✓
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          </Form.Item>

          <Form.Item
            name="description"
            label="描述（可选）"
          >
            <TextArea rows={2} placeholder="请输入Agent描述" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setCreateModalVisible(false);
                setSelectedType('');
                form.resetFields();
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={loading}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 配置Agent Drawer */}
      <Drawer
        title={`配置 ${selectedAgent?.name}`}
        width={720}
        open={configDrawerVisible}
        onClose={() => {
          setConfigDrawerVisible(false);
          setLoading(false);
        }}
        destroyOnClose
      >
        {selectedAgent && (
          <AgentConfigForm
            agentType={selectedAgent.type}
            initialConfig={selectedAgent.config || {}}
            onSubmit={handleSaveConfig}
            onCancel={() => {
              setConfigDrawerVisible(false);
              setLoading(false);
            }}
            loading={loading}
          />
        )}
      </Drawer>

      {/* 执行历史 Drawer */}
      <Drawer
        title={`${selectedAgent?.name} 执行历史`}
        width={900}
        open={historyDrawerVisible}
        onClose={() => {
          setHistoryDrawerVisible(false);
          setSearchText('');
          setStatusFilter('all');
        }}
      >
        {/* 搜索和筛选 */}
        <Space style={{ marginBottom: 16, width: '100%' }} direction="vertical">
          <Space style={{ width: '100%' }}>
            <Input.Search
              placeholder="搜索执行记录（输入/输出内容）"
              value={searchText}
              onChange={(e) => handleSearch(e.target.value)}
              onSearch={handleSearch}
              style={{ width: 400 }}
              allowClear
            />
            <Select
              placeholder="筛选状态"
              value={statusFilter}
              onChange={handleStatusFilter}
              style={{ width: 150 }}
            >
              <Option value="all">全部状态</Option>
              <Option value="completed">成功</Option>
              <Option value="failed">失败</Option>
              <Option value="running">运行中</Option>
            </Select>
            <Text type="secondary" style={{ marginLeft: 'auto' }}>
              共 {filteredExecutions.length} 条记录
            </Text>
          </Space>
        </Space>

        <Table
          columns={executionColumns}
          dataSource={filteredExecutions}
          rowKey="id"
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          size="small"
        />
      </Drawer>

      {/* Agent执行对话框 */}
      <AgentExecutionDialog
        visible={executionDialogVisible}
        agent={selectedAgent}
        onClose={() => {
          setExecutionDialogVisible(false);
          setSelectedAgent(null);
        }}
        onExecute={executeAgent}
      />
    </div>
  );
};

export default AgentPage;
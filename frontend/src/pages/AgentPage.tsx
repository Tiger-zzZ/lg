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
  JsonInput
} from 'antd';
import {
  PlusOutlined,
  RobotOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  HistoryOutlined,
  EyeOutlined
} from '@ant-design/icons';
import MarkdownRenderer from '../components/MarkdownRenderer';

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
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [form] = Form.useForm();
  const [configForm] = Form.useForm();

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

      const response = await fetch('/api/v1/agents/', {
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
    const input = prompt('请输入要发送给Agent的消息:');
    if (!input) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/agents/execute/${agent.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          messages: [input],
          metadata: {}
        }),
      });

      if (response.ok) {
        const result = await response.json();
        Modal.info({
          title: `${agent.name} 执行结果`,
          content: (
            <div>
              <p><strong>状态:</strong> {result.status}</p>
              <p><strong>结果:</strong></p>
              <div style={{ maxHeight: '400px', overflow: 'auto', border: '1px solid #f0f0f0', padding: '12px', borderRadius: '6px' }}>
                <MarkdownRenderer content={result.result} />
              </div>
              {result.duration && (
                <p><strong>执行时长:</strong> {result.duration}ms</p>
              )}
            </div>
          ),
          width: 800,
        });
        loadAgents(); // 更新状态
      } else {
        const error = await response.json();
        message.error(error.detail || 'Agent执行失败');
      }
    } catch (error) {
      console.error('执行Agent失败:', error);
      message.error('网络错误，请稍后重试');
    }
  };

  const handleToggleAgent = async (agent: Agent) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`/api/v1/agents/toggle/${agent.id}`, {
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

      const response = await fetch(`/api/v1/agents/delete/${agent.id}`, {
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
    configForm.setFieldsValue({
      config: JSON.stringify(agent.config || {}, null, 2)
    });
    setConfigDrawerVisible(true);
  };

  const handleSaveConfig = async (values: any) => {
    if (!selectedAgent) return;

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const config = JSON.parse(values.config);
      const response = await fetch(`/api/v1/agents/config/${selectedAgent.id}`, {
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
      message.error('配置格式错误，请检查JSON格式');
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

      const response = await fetch(`/api/v1/agents/executions/${agent.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const executionList = await response.json();
        setExecutions(executionList);
        setHistoryDrawerVisible(true);
      } else {
        message.error('加载执行历史失败');
      }
    } catch (error) {
      console.error('加载执行历史失败:', error);
      message.error('网络错误，请稍后重试');
    }
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
      render: (_, record: AgentExecution) => (
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
        >
          查看详情
        </Button>
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
              <p><strong>类型:</strong> {agent.type}</p>
              <p><strong>描述:</strong> {agent.description || '暂无描述'}</p>
              <p><strong>创建时间:</strong> {new Date(agent.created_at).toLocaleString()}</p>
              {agent.last_used_at && (
                <p><strong>最后使用:</strong> {new Date(agent.last_used_at).toLocaleString()}</p>
              )}

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
          form.resetFields();
        }}
        footer={null}
        width={600}
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
            label="Agent类型"
            rules={[{ required: true, message: '请选择Agent类型' }]}
          >
            <Select placeholder="请选择Agent类型">
              <Option value="rag">RAG Agent - 文档问答</Option>
              <Option value="chat">Chat Agent - 对话助手</Option>
              <Option value="search">Search Agent - 搜索助手</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="请输入Agent描述" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setCreateModalVisible(false);
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
        width={600}
        open={configDrawerVisible}
        onClose={() => setConfigDrawerVisible(false)}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setConfigDrawerVisible(false)}>
              取消
            </Button>
            <Button type="primary" onClick={() => configForm.submit()}>
              保存配置
            </Button>
          </Space>
        }
      >
        <Form
          form={configForm}
          layout="vertical"
          onFinish={handleSaveConfig}
        >
          <Form.Item
            name="config"
            label="Agent配置 (JSON格式)"
            rules={[
              { required: true, message: '请输入配置' },
              {
                validator: (_, value) => {
                  try {
                    JSON.parse(value);
                    return Promise.resolve();
                  } catch {
                    return Promise.reject(new Error('请输入有效的JSON格式'));
                  }
                }
              }
            ]}
          >
            <TextArea
              rows={15}
              placeholder='{"key": "value"}'
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
        </Form>
      </Drawer>

      {/* 执行历史 Drawer */}
      <Drawer
        title={`${selectedAgent?.name} 执行历史`}
        width={800}
        open={historyDrawerVisible}
        onClose={() => setHistoryDrawerVisible(false)}
      >
        <Table
          columns={executionColumns}
          dataSource={executions}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Drawer>
    </div>
  );
};

export default AgentPage;
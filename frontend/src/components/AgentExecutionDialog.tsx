import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Space,
  Alert,
  Spin,
  Progress,
  Card,
  Select,
  Typography,
  message,
  Tooltip,
  Divider
} from 'antd';
import {
  PlayCircleOutlined,
  CopyOutlined,
  DownloadOutlined,
  MessageOutlined,
  CloseOutlined
} from '@ant-design/icons';
import MarkdownRenderer from './MarkdownRenderer';

const { TextArea } = Input;
const { Option } = Select;
const { Title, Text } = Typography;

interface Agent {
  id: string;
  name: string;
  type: string;
  description?: string;
}

interface ExecutionResult {
  status: string;
  result: string;
  duration?: number;
  error?: string;
}

interface AgentExecutionDialogProps {
  visible: boolean;
  agent: Agent | null;
  onClose: () => void;
  onExecute: (input: string, continueConversation?: boolean) => Promise<ExecutionResult>;
}

// Agent类型使用提示
const AGENT_USAGE_TIPS: Record<string, string> = {
  search: '💡 搜索助手能够帮您在知识库中查找相关文档。\n\n示例：\n• "帮我搜索关于Python异步编程的文档"\n• "查找有关微服务架构的资料"',
  chat: '💡 对话助手可以回答各种问题并进行自然对话。\n\n示例：\n• "用简单的语言解释量子计算"\n• "帮我分析一下这个商业方案"',
  rag: '💡 RAG Agent能够基于文档内容回答问题。\n\n示例：\n• "根据上传的文档，总结项目的核心功能"\n• "文档中提到的技术栈有哪些？"',
  data_analyst: '💡 数据分析师能够进行数据分析和统计计算。\n\n示例：\n• "计算 15 + 3 * 4"\n• "帮我分析这组数据的趋势"\n• "查询文档表的统计信息"'
};

// 快捷输入模板
const INPUT_TEMPLATES: Record<string, Array<{ label: string; value: string }>> = {
  search: [
    { label: '文档搜索', value: '帮我搜索关于{主题}的文档' },
    { label: '关键词查找', value: '查找包含"{关键词}"的所有内容' },
    { label: '主题总结', value: '总结所有关于{主题}的文档内容' }
  ],
  chat: [
    { label: '概念解释', value: '用简单的语言解释{概念}' },
    { label: '方案分析', value: '帮我分析{方案}的优缺点' },
    { label: '问题解答', value: '{你的问题}' }
  ],
  rag: [
    { label: '文档总结', value: '总结文档的核心内容' },
    { label: '信息提取', value: '从文档中提取{信息类型}' },
    { label: '问答', value: '根据文档回答：{你的问题}' }
  ],
  data_analyst: [
    { label: '数值计算', value: '计算 {表达式}' },
    { label: '数据统计', value: '统计 {数据} 的平均值' },
    { label: '数据库查询', value: '查询{表名}的统计信息' }
  ]
};

const AgentExecutionDialog: React.FC<AgentExecutionDialogProps> = ({
  visible,
  agent,
  onClose,
  onExecute
}) => {
  const [form] = Form.useForm();
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [progress, setProgress] = useState(0);
  const [conversationHistory, setConversationHistory] = useState<Array<{ input: string; output: string }>>([]);

  // 重置状态
  useEffect(() => {
    if (visible) {
      setResult(null);
      setProgress(0);
      setConversationHistory([]);
      form.resetFields();
    }
  }, [visible, form]);

  // 获取Agent类型提示
  const getUsageTips = () => {
    if (!agent) return '';
    return AGENT_USAGE_TIPS[agent.type] || '💡 请输入您的指令或问题';
  };

  // 获取模板列表
  const getTemplates = () => {
    if (!agent) return [];
    return INPUT_TEMPLATES[agent.type] || [];
  };

  // 应用模板
  const applyTemplate = (templateValue: string) => {
    form.setFieldsValue({ input: templateValue });
  };

  // 执行Agent
  const handleExecute = async (continueConversation = false) => {
    try {
      const values = await form.validateFields();
      const input = values.input?.trim();

      if (!input) {
        message.warning('请输入内容');
        return;
      }

      setExecuting(true);
      setProgress(0);

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 300);

      try {
        const executionResult = await onExecute(input, continueConversation);

        clearInterval(progressInterval);
        setProgress(100);
        setResult(executionResult);

        // 添加到对话历史
        if (executionResult.status === 'completed') {
          setConversationHistory(prev => [
            ...prev,
            { input, output: executionResult.result }
          ]);
        }

        // 如果不是继续对话，清空输入框
        if (!continueConversation) {
          form.setFieldsValue({ input: '' });
        }
      } catch (error: any) {
        clearInterval(progressInterval);
        setProgress(0);
        message.error(error.message || '执行失败');
      } finally {
        setExecuting(false);
      }
    } catch (error) {
      // 表单验证失败
      setExecuting(false);
    }
  };

  // 复制结果
  const handleCopy = () => {
    if (result?.result) {
      navigator.clipboard.writeText(result.result);
      message.success('已复制到剪贴板');
    }
  };

  // 导出结果
  const handleExport = () => {
    if (result?.result) {
      const blob = new Blob([result.result], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agent-result-${Date.now()}.md`;
      a.click();
      URL.revokeObjectURL(url);
      message.success('导出成功');
    }
  };

  // 继续对话
  const handleContinue = () => {
    handleExecute(true);
  };

  return (
    <Modal
      title={
        <Space>
          <PlayCircleOutlined />
          <span>执行 {agent?.name || 'Agent'}</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={1200}
      footer={null}
      destroyOnClose
    >
      <div style={{ display: 'flex', gap: 16, minHeight: 500, width: '100%' }}>
        {/* 左侧：输入区 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
          <Form form={form} layout="vertical">
            <Form.Item
              name="input"
              label="输入内容"
              rules={[{ required: true, message: '请输入内容' }]}
            >
              <TextArea
                rows={8}
                placeholder="请输入要发送给Agent的消息..."
                autoSize={{ minRows: 8, maxRows: 16 }}
                disabled={executing}
                style={{ width: '100%', maxWidth: '100%' }}
              />
            </Form.Item>

            {/* 使用提示 */}
            <Alert
              message="使用提示"
              description={<pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit', wordBreak: 'break-word', maxWidth: '100%' }}>{getUsageTips()}</pre>}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            {/* 快捷模板 */}
            {getTemplates().length > 0 && (
              <Form.Item label="快捷模板">
                <Select
                  placeholder="选择模板快速输入"
                  onChange={applyTemplate}
                  disabled={executing}
                  allowClear
                >
                  {getTemplates().map((template, index) => (
                    <Option key={index} value={template.value}>
                      {template.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            )}

            {/* 操作按钮 */}
            <Space>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleExecute(false)}
                loading={executing}
                size="large"
              >
                执行
              </Button>
              <Button
                icon={<CloseOutlined />}
                onClick={onClose}
                disabled={executing}
              >
                关闭
              </Button>
            </Space>
          </Form>

          {/* 对话历史 */}
          {conversationHistory.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <Divider>对话历史</Divider>
              <div style={{ maxHeight: 200, overflow: 'auto' }}>
                {conversationHistory.map((conv, index) => (
                  <Card key={index} size="small" style={{ marginBottom: 8 }}>
                    <div style={{ wordBreak: 'break-word', overflow: 'hidden' }}>
                      <Text strong>输入:</Text> <Text>{conv.input}</Text>
                      <br />
                      <Text strong>输出:</Text> <Text type="secondary" ellipsis>{conv.output.substring(0, 100)}...</Text>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右侧：执行状态和结果 */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
          <Title level={5}>执行结果</Title>

          {/* 执行中状态 */}
          {executing && (
            <Card style={{ marginBottom: 16 }}>
              <Spin tip="Agent正在处理您的请求...">
                <div style={{ padding: '20px 0' }}>
                  <Progress percent={progress} status="active" />
                </div>
              </Spin>
            </Card>
          )}

          {/* 执行结果 */}
          {result && (
            <>
              <Card
                style={{ marginBottom: 16 }}
                bodyStyle={{
                  padding: 24,
                  maxHeight: '60vh',
                  overflowY: 'auto'
                }}
              >
                {result.status === 'completed' ? (
                  <div>
                    {/* 成功状态指示器 */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: 20,
                      padding: '10px 14px',
                      background: '#f0f9ff',
                      borderRadius: 6,
                      borderLeft: '4px solid #1890ff'
                    }}>
                      <span style={{ fontSize: 16, marginRight: 8, color: '#1890ff' }}>✓</span>
                      <Text strong style={{ color: '#1890ff' }}>执行成功</Text>
                      {result.duration && (
                        <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                          ⚡ {result.duration}ms
                        </Text>
                      )}
                    </div>

                    {/* Markdown内容 */}
                    <div className="agent-result-content">
                      <MarkdownRenderer content={result.result} />
                    </div>
                  </div>
                ) : result.status === 'failed' ? (
                  <Alert
                    message="执行失败"
                    description={result.error || '未知错误'}
                    type="error"
                    showIcon
                  />
                ) : (
                  <Alert
                    message={`状态: ${result.status}`}
                    type="info"
                    showIcon
                  />
                )}
              </Card>

              {/* 结果操作按钮 */}
              {result.status === 'completed' && (
                <Space>
                  <Tooltip title="继续对话">
                    <Button
                      icon={<MessageOutlined />}
                      onClick={handleContinue}
                      disabled={executing}
                    >
                      继续对话
                    </Button>
                  </Tooltip>
                  <Tooltip title="复制结果">
                    <Button
                      icon={<CopyOutlined />}
                      onClick={handleCopy}
                    >
                      复制
                    </Button>
                  </Tooltip>
                  <Tooltip title="导出为Markdown文件">
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={handleExport}
                    >
                      导出
                    </Button>
                  </Tooltip>
                </Space>
              )}
            </>
          )}

          {/* 无结果时的提示 */}
          {!result && !executing && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                padding: '60px 20px',
                background: '#fafafa',
                border: '2px dashed #d9d9d9',
                borderRadius: 8
              }}
            >
              <div style={{
                fontSize: 48,
                opacity: 0.3,
                marginBottom: 16
              }}>
                📝
              </div>
              <Text type="secondary" style={{ fontSize: 15, marginBottom: 8 }}>
                执行结果将显示在这里
              </Text>
              <Text type="secondary" style={{ fontSize: 13 }}>
                请在左侧输入内容并点击"执行"按钮
              </Text>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default AgentExecutionDialog;
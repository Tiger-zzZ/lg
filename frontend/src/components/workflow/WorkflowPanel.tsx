import React, { useState, useEffect } from 'react';
import { Form, Input, Select, Button, Space, Card, Divider, Switch, InputNumber } from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';

import type { WorkflowNode } from './WorkflowEditor';

const { TextArea } = Input;

interface WorkflowPanelProps {
  node: WorkflowNode;
  onUpdate: (node: WorkflowNode) => void;
  onClose: () => void;
}

const WorkflowPanel: React.FC<WorkflowPanelProps> = ({ node, onUpdate, onClose }) => {
  const [form] = Form.useForm();
  const [hasChanges, setHasChanges] = useState(false);

  // 初始化表单数据
  useEffect(() => {
    form.setFieldsValue({
      label: node.data.label,
      agentType: node.data.agentType,
      condition: node.data.condition,
      mergeStrategy: node.data.mergeStrategy,
      config: node.data.config || {},
    });
    setHasChanges(false);
  }, [node, form]);

  // 表单值变化处理
  const handleFormChange = () => {
    setHasChanges(true);
  };

  // 保存配置
  const handleSave = () => {
    form.validateFields().then((values) => {
      const updatedNode: WorkflowNode = {
        ...node,
        data: {
          ...node.data,
          label: values.label,
          agentType: values.agentType,
          condition: values.condition,
          mergeStrategy: values.mergeStrategy,
          config: values.config,
        },
      };

      onUpdate(updatedNode);
      setHasChanges(false);
    });
  };

  // 重置配置
  const handleReset = () => {
    form.resetFields();
    setHasChanges(false);
  };

  // 获取Agent类型选项
  const getAgentTypeOptions = () => [
    { value: 'research', label: '研究Agent' },
    { value: 'coding', label: '编程Agent' },
    { value: 'writing', label: '写作Agent' },
    { value: 'rag', label: 'RAG Agent' },
  ];

  // 获取合并策略选项
  const getMergeStrategyOptions = () => [
    { value: 'all', label: '等待所有输入' },
    { value: 'any', label: '任意输入到达' },
    { value: 'majority', label: '大多数输入' },
    { value: 'priority', label: '优先级合并' },
  ];

  // 渲染Agent节点配置
  const renderAgentConfig = () => (
    <>
      <Form.Item
        name="agentType"
        label="Agent类型"
        rules={[{ required: true, message: '请选择Agent类型' }]}
      >
        <Select options={getAgentTypeOptions()} />
      </Form.Item>

      <Divider>Agent配置</Divider>

      <Form.Item name={['config', 'systemPrompt']} label="系统提示">
        <TextArea rows={3} placeholder="输入系统提示词..." />
      </Form.Item>

      <Form.Item name={['config', 'temperature']} label="温度参数">
        <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name={['config', 'maxTokens']} label="最大Token数">
        <InputNumber min={1} max={4000} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name={['config', 'timeout']} label="超时时间(秒)">
        <InputNumber min={1} max={300} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name={['config', 'retryCount']} label="重试次数">
        <InputNumber min={0} max={5} style={{ width: '100%' }} />
      </Form.Item>
    </>
  );

  // 渲染条件节点配置
  const renderConditionConfig = () => (
    <>
      <Form.Item
        name="condition"
        label="条件表达式"
        rules={[{ required: true, message: '请输入条件表达式' }]}
      >
        <TextArea
          rows={4}
          placeholder="输入JavaScript条件表达式，如：result.success === true"
        />
      </Form.Item>

      <Divider>条件配置</Divider>

      <Form.Item name={['config', 'trueLabel']} label="True分支标签">
        <Input placeholder="成功" />
      </Form.Item>

      <Form.Item name={['config', 'falseLabel']} label="False分支标签">
        <Input placeholder="失败" />
      </Form.Item>

      <Form.Item name={['config', 'timeout']} label="评估超时(秒)">
        <InputNumber min={1} max={60} style={{ width: '100%' }} />
      </Form.Item>
    </>
  );

  // 渲染合并节点配置
  const renderMergeConfig = () => (
    <>
      <Form.Item
        name="mergeStrategy"
        label="合并策略"
        rules={[{ required: true, message: '请选择合并策略' }]}
      >
        <Select options={getMergeStrategyOptions()} />
      </Form.Item>

      <Divider>合并配置</Divider>

      <Form.Item name={['config', 'waitTimeout']} label="等待超时(秒)">
        <InputNumber min={1} max={600} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item name={['config', 'combineResults']} label="合并结果" valuePropName="checked">
        <Switch />
      </Form.Item>

      <Form.Item name={['config', 'priorityOrder']} label="优先级顺序">
        <Input placeholder="input1,input2" />
      </Form.Item>
    </>
  );

  return (
    <div style={{ padding: '16px 0' }}>
      <Card
        title={`配置节点: ${node.data.label}`}
        size="small"
        extra={
          <Space>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={handleReset}
              disabled={!hasChanges}
            >
              重置
            </Button>
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              onClick={handleSave}
              disabled={!hasChanges}
            >
              保存
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onValuesChange={handleFormChange}
          size="small"
        >
          {/* 基础配置 */}
          <Form.Item
            name="label"
            label="节点名称"
            rules={[{ required: true, message: '请输入节点名称' }]}
          >
            <Input placeholder="输入节点名称" />
          </Form.Item>

          {/* 根据节点类型渲染不同配置 */}
          {node.type === 'agent' && renderAgentConfig()}
          {node.type === 'condition' && renderConditionConfig()}
          {node.type === 'merge' && renderMergeConfig()}

          <Divider>高级设置</Divider>

          <Form.Item name={['config', 'description']} label="节点描述">
            <TextArea rows={2} placeholder="可选：节点功能描述" />
          </Form.Item>

          <Form.Item name={['config', 'enabled']} label="启用节点" valuePropName="checked">
            <Switch defaultChecked />
          </Form.Item>

          <Form.Item name={['config', 'logLevel']} label="日志级别">
            <Select
              placeholder="选择日志级别"
              options={[
                { value: 'debug', label: 'Debug' },
                { value: 'info', label: 'Info' },
                { value: 'warning', label: 'Warning' },
                { value: 'error', label: 'Error' },
              ]}
            />
          </Form.Item>
        </Form>

        {hasChanges && (
          <div style={{
            marginTop: 16,
            padding: 8,
            background: '#fff7e6',
            border: '1px solid #ffd591',
            borderRadius: 4,
            fontSize: 12
          }}>
            配置已修改，请保存后生效
          </div>
        )}
      </Card>

      <div style={{ marginTop: 16, textAlign: 'right' }}>
        <Space>
          <Button onClick={onClose}>
            关闭
          </Button>
          <Button type="primary" onClick={handleSave} disabled={!hasChanges}>
            应用并关闭
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default WorkflowPanel;
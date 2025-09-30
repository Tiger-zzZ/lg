import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Slider,
  Select,
  Switch,
  Button,
  Space,
  Alert,
  Tooltip,
  Tabs,
  Card,
  message
} from 'antd';
import {
  InfoCircleOutlined,
  ThunderboltOutlined,
  EditOutlined,
  CheckOutlined
} from '@ant-design/icons';
import { AGENT_TYPE_INFO, AgentTypeInfo, ConfigField } from '../constants/agentTypes';

const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

interface AgentConfigFormProps {
  agentType: string;
  initialConfig?: Record<string, any>;
  onSubmit: (config: Record<string, any>) => void;
  onCancel?: () => void;
  loading?: boolean;
}

const AgentConfigForm: React.FC<AgentConfigFormProps> = ({
  agentType,
  initialConfig = {},
  onSubmit,
  onCancel,
  loading = false
}) => {
  const [form] = Form.useForm();
  const [mode, setMode] = useState<'form' | 'json'>('form');
  const [jsonValue, setJsonValue] = useState('');
  const [jsonError, setJsonError] = useState('');

  const typeInfo: AgentTypeInfo | undefined = AGENT_TYPE_INFO[agentType];

  useEffect(() => {
    if (typeInfo) {
      // 初始化表单值
      const defaultValues: Record<string, any> = {};
      Object.entries(typeInfo.configSchema).forEach(([key, field]) => {
        defaultValues[key] = initialConfig[key] !== undefined ? initialConfig[key] : field.default;
      });
      form.setFieldsValue(defaultValues);

      // 初始化JSON值
      setJsonValue(JSON.stringify(initialConfig || defaultValues, null, 2));
    }
  }, [agentType, initialConfig, typeInfo, form]);

  // 渲染配置项
  const renderConfigField = (key: string, field: ConfigField) => {
    const commonProps = {
      disabled: loading
    };

    switch (field.type) {
      case 'slider':
        return (
          <div>
            <Slider
              {...commonProps}
              min={field.min || 0}
              max={field.max || 1}
              step={field.step || 0.1}
              marks={{
                [field.min || 0]: field.min?.toString() || '0',
                [field.max || 1]: field.max?.toString() || '1'
              }}
            />
          </div>
        );

      case 'number':
        return (
          <InputNumber
            {...commonProps}
            min={field.min}
            max={field.max}
            step={field.step || 1}
            style={{ width: '100%' }}
            placeholder={field.placeholder}
          />
        );

      case 'select':
        return (
          <Select
            {...commonProps}
            placeholder={field.placeholder || '请选择'}
            style={{ width: '100%' }}
          >
            {field.options?.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        );

      case 'textarea':
        return (
          <TextArea
            {...commonProps}
            rows={4}
            placeholder={field.placeholder}
          />
        );

      case 'input':
      default:
        return (
          <Input
            {...commonProps}
            placeholder={field.placeholder}
          />
        );
    }
  };

  // 应用模板
  const applyTemplate = (templateConfig: Record<string, any>) => {
    form.setFieldsValue(templateConfig);
    setJsonValue(JSON.stringify(templateConfig, null, 2));
    message.success('模板已应用');
  };

  // 表单提交
  const handleFormSubmit = async () => {
    try {
      if (mode === 'form') {
        const values = await form.validateFields();
        onSubmit(values);
      } else {
        // JSON模式
        try {
          const config = JSON.parse(jsonValue);
          onSubmit(config);
        } catch (error) {
          setJsonError('JSON格式错误，请检查');
          message.error('JSON格式错误');
        }
      }
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  // 表单值变化时同步到JSON
  const handleFormChange = () => {
    const values = form.getFieldsValue();
    setJsonValue(JSON.stringify(values, null, 2));
  };

  // JSON变化时尝试同步到表单
  const handleJsonChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setJsonValue(value);
    setJsonError('');

    try {
      const config = JSON.parse(value);
      form.setFieldsValue(config);
    } catch (error) {
      // JSON格式错误，不更新表单
      setJsonError('JSON格式错误');
    }
  };

  if (!typeInfo) {
    return (
      <Alert
        message="错误"
        description={`未找到Agent类型 "${agentType}" 的配置信息`}
        type="error"
        showIcon
      />
    );
  }

  return (
    <div>
      {/* Agent类型信息 */}
      <Alert
        message={typeInfo.name}
        description={typeInfo.detailedDescription}
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 配置模板 */}
      {typeInfo.configTemplates && typeInfo.configTemplates.length > 0 && (
        <Card
          title="配置模板"
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Space wrap>
            {typeInfo.configTemplates.map((template, index) => (
              <Tooltip key={index} title={template.description}>
                <Button
                  size="small"
                  icon={<ThunderboltOutlined />}
                  onClick={() => applyTemplate(template.config)}
                  disabled={loading}
                >
                  {template.name}
                </Button>
              </Tooltip>
            ))}
          </Space>
        </Card>
      )}

      {/* 编辑模式切换 */}
      <Tabs
        activeKey={mode}
        onChange={(key) => setMode(key as 'form' | 'json')}
        style={{ marginBottom: 16 }}
      >
        <TabPane
          tab={
            <span>
              <EditOutlined /> 表单模式
            </span>
          }
          key="form"
        >
          <Form
            form={form}
            layout="vertical"
            onValuesChange={handleFormChange}
          >
            {Object.entries(typeInfo.configSchema).map(([key, field]) => (
              <Form.Item
                key={key}
                name={key}
                label={
                  <Space>
                    <span>{field.label}</span>
                    {field.tooltip && (
                      <Tooltip title={field.tooltip}>
                        <InfoCircleOutlined style={{ color: '#999' }} />
                      </Tooltip>
                    )}
                  </Space>
                }
                rules={[
                  {
                    required: field.required !== false,
                    message: `请输入${field.label}`
                  }
                ]}
                extra={field.description}
              >
                {renderConfigField(key, field)}
              </Form.Item>
            ))}
          </Form>
        </TabPane>

        <TabPane
          tab={
            <span>
              <CheckOutlined /> JSON模式
            </span>
          }
          key="json"
        >
          <div>
            <Alert
              message="高级模式"
              description="直接编辑JSON配置，适合高级用户。请确保JSON格式正确。"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <TextArea
              value={jsonValue}
              onChange={handleJsonChange}
              rows={15}
              placeholder='{"key": "value"}'
              style={{ fontFamily: 'monospace', fontSize: 12 }}
              disabled={loading}
            />
            {jsonError && (
              <Alert
                message={jsonError}
                type="error"
                showIcon
                style={{ marginTop: 8 }}
              />
            )}
          </div>
        </TabPane>
      </Tabs>

      {/* 操作按钮 */}
      <div style={{ textAlign: 'right' }}>
        <Space>
          {onCancel && (
            <Button onClick={onCancel} disabled={loading}>
              取消
            </Button>
          )}
          <Button
            type="primary"
            onClick={handleFormSubmit}
            loading={loading}
          >
            保存配置
          </Button>
        </Space>
      </div>
    </div>
  );
};

export default AgentConfigForm;
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Modal,
  Form,
  Input,
  Select,
  List,
  Space,
  Tag,
  Popconfirm,
  message,
  Upload,
  Divider,
} from 'antd';
import {
  SaveOutlined,
  FolderOpenOutlined,
  UploadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  CopyOutlined,
  StarOutlined,
  StarFilled,
} from '@ant-design/icons';

import type { WorkflowNode, WorkflowEdge } from './WorkflowEditor';

const { TextArea } = Input;

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt: Date;
  updatedAt: Date;
  isStarred: boolean;
  thumbnail?: string;
  metadata: {
    nodeCount: number;
    complexity: 'simple' | 'medium' | 'complex';
    estimatedDuration: number;
  };
}

interface WorkflowTemplateManagerProps {
  currentWorkflow?: { nodes: WorkflowNode[]; edges: WorkflowEdge[] };
  onLoadTemplate: (template: WorkflowTemplate) => void;
  onWorkflowChange?: (workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => void;
}

// 预定义模板
const DEFAULT_TEMPLATES: WorkflowTemplate[] = [
  {
    id: 'template_1',
    name: '文档分析工作流',
    description: '使用RAG Agent分析上传的文档，提取关键信息并生成摘要',
    category: '文档处理',
    tags: ['RAG', '文档', '分析'],
    nodes: [
      {
        id: 'node_1',
        type: 'agent',
        position: { x: 100, y: 100 },
        data: {
          label: '文档预处理',
          agentType: 'research',
          status: 'idle',
        },
      },
      {
        id: 'node_2',
        type: 'agent',
        position: { x: 300, y: 100 },
        data: {
          label: 'RAG分析',
          agentType: 'rag',
          status: 'idle',
        },
      },
      {
        id: 'node_3',
        type: 'agent',
        position: { x: 500, y: 100 },
        data: {
          label: '摘要生成',
          agentType: 'writing',
          status: 'idle',
        },
      },
    ],
    edges: [
      {
        id: 'edge_1',
        source: 'node_1',
        target: 'node_2',
        type: 'smoothstep',
        animated: true,
      },
      {
        id: 'edge_2',
        source: 'node_2',
        target: 'node_3',
        type: 'smoothstep',
        animated: true,
      },
    ],
    createdAt: new Date('2024-01-01'),
    updatedAt: new Date('2024-01-01'),
    isStarred: true,
    metadata: {
      nodeCount: 3,
      complexity: 'simple',
      estimatedDuration: 5,
    },
  },
  {
    id: 'template_2',
    name: '代码审查工作流',
    description: '自动化代码审查，包括语法检查、最佳实践验证和安全扫描',
    category: '代码审查',
    tags: ['代码', '审查', '自动化'],
    nodes: [
      {
        id: 'node_1',
        type: 'agent',
        position: { x: 100, y: 50 },
        data: {
          label: '代码获取',
          agentType: 'research',
          status: 'idle',
        },
      },
      {
        id: 'node_2',
        type: 'agent',
        position: { x: 300, y: 50 },
        data: {
          label: '语法检查',
          agentType: 'coding',
          status: 'idle',
        },
      },
      {
        id: 'node_3',
        type: 'condition',
        position: { x: 500, y: 50 },
        data: {
          label: '检查结果',
          condition: 'result.errors === 0',
          status: 'idle',
        },
      },
      {
        id: 'node_4',
        type: 'agent',
        position: { x: 300, y: 200 },
        data: {
          label: '修复建议',
          agentType: 'coding',
          status: 'idle',
        },
      },
      {
        id: 'node_5',
        type: 'agent',
        position: { x: 700, y: 50 },
        data: {
          label: '生成报告',
          agentType: 'writing',
          status: 'idle',
        },
      },
    ],
    edges: [
      {
        id: 'edge_1',
        source: 'node_1',
        target: 'node_2',
        type: 'smoothstep',
      },
      {
        id: 'edge_2',
        source: 'node_2',
        target: 'node_3',
        type: 'smoothstep',
      },
      {
        id: 'edge_3',
        source: 'node_3',
        target: 'node_4',
        sourceHandle: 'false',
        type: 'smoothstep',
      },
      {
        id: 'edge_4',
        source: 'node_3',
        target: 'node_5',
        sourceHandle: 'true',
        type: 'smoothstep',
      },
      {
        id: 'edge_5',
        source: 'node_4',
        target: 'node_5',
        type: 'smoothstep',
      },
    ],
    createdAt: new Date('2024-01-02'),
    updatedAt: new Date('2024-01-02'),
    isStarred: false,
    metadata: {
      nodeCount: 5,
      complexity: 'medium',
      estimatedDuration: 10,
    },
  },
];

const WorkflowTemplateManager: React.FC<WorkflowTemplateManagerProps> = ({
  currentWorkflow,
  onLoadTemplate,
  onWorkflowChange,
}) => {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>(DEFAULT_TEMPLATES);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isSaveModalVisible, setIsSaveModalVisible] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [form] = Form.useForm();

  // 从localStorage加载用户模板
  useEffect(() => {
    const savedTemplates = localStorage.getItem('workflow_templates');
    if (savedTemplates) {
      try {
        const parsed = JSON.parse(savedTemplates);
        setTemplates(prev => [...DEFAULT_TEMPLATES, ...parsed]);
      } catch (error) {
        console.error('加载模板失败:', error);
      }
    }
  }, []);

  // 保存模板到localStorage
  const saveTemplates = (newTemplates: WorkflowTemplate[]) => {
    const userTemplates = newTemplates.filter(t => !DEFAULT_TEMPLATES.find(dt => dt.id === t.id));
    localStorage.setItem('workflow_templates', JSON.stringify(userTemplates));
  };

  // 保存当前工作流为模板
  const handleSaveTemplate = () => {
    if (!currentWorkflow) {
      message.error('没有可保存的工作流');
      return;
    }

    form.validateFields().then((values) => {
      const newTemplate: WorkflowTemplate = {
        id: `template_${Date.now()}`,
        name: values.name,
        description: values.description,
        category: values.category,
        tags: values.tags || [],
        nodes: currentWorkflow.nodes,
        edges: currentWorkflow.edges,
        createdAt: new Date(),
        updatedAt: new Date(),
        isStarred: false,
        metadata: {
          nodeCount: currentWorkflow.nodes.length,
          complexity: currentWorkflow.nodes.length <= 3 ? 'simple' : currentWorkflow.nodes.length <= 6 ? 'medium' : 'complex',
          estimatedDuration: Math.ceil(currentWorkflow.nodes.length * 2),
        },
      };

      const updatedTemplates = [...templates, newTemplate];
      setTemplates(updatedTemplates);
      saveTemplates(updatedTemplates);

      message.success('模板保存成功');
      setIsSaveModalVisible(false);
      form.resetFields();
    });
  };

  // 加载模板
  const handleLoadTemplate = (template: WorkflowTemplate) => {
    onLoadTemplate(template);
    message.success(`已加载模板: ${template.name}`);
    setIsModalVisible(false);
  };

  // 删除模板
  const handleDeleteTemplate = (templateId: string) => {
    if (DEFAULT_TEMPLATES.find(t => t.id === templateId)) {
      message.error('无法删除预定义模板');
      return;
    }

    const updatedTemplates = templates.filter(t => t.id !== templateId);
    setTemplates(updatedTemplates);
    saveTemplates(updatedTemplates);
    message.success('模板删除成功');
  };

  // 收藏/取消收藏模板
  const handleToggleStar = (templateId: string) => {
    const updatedTemplates = templates.map(t =>
      t.id === templateId ? { ...t, isStarred: !t.isStarred } : t
    );
    setTemplates(updatedTemplates);
    saveTemplates(updatedTemplates);
  };

  // 复制模板
  const handleCopyTemplate = (template: WorkflowTemplate) => {
    const copiedTemplate: WorkflowTemplate = {
      ...template,
      id: `template_${Date.now()}`,
      name: `${template.name} (副本)`,
      createdAt: new Date(),
      updatedAt: new Date(),
      isStarred: false,
    };

    const updatedTemplates = [...templates, copiedTemplate];
    setTemplates(updatedTemplates);
    saveTemplates(updatedTemplates);
    message.success('模板复制成功');
  };

  // 导出模板
  const handleExportTemplate = (template: WorkflowTemplate) => {
    const dataStr = JSON.stringify(template, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${template.name.replace(/\s+/g, '_')}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 导入模板
  const handleImportTemplate = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importedTemplate = JSON.parse(e.target?.result as string) as WorkflowTemplate;
        importedTemplate.id = `template_${Date.now()}`;
        importedTemplate.createdAt = new Date();
        importedTemplate.updatedAt = new Date();

        const updatedTemplates = [...templates, importedTemplate];
        setTemplates(updatedTemplates);
        saveTemplates(updatedTemplates);
        message.success('模板导入成功');
      } catch (error) {
        message.error('模板文件格式错误');
      }
    };
    reader.readAsText(file);
    return false; // 阻止上传
  };

  // 获取分类选项
  const categories = ['all', ...Array.from(new Set(templates.map(t => t.category)))];

  // 过滤模板
  const filteredTemplates = templates.filter(template => {
    const matchesCategory = selectedCategory === 'all' || template.category === selectedCategory;
    const matchesSearch = searchQuery === '' ||
      template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));

    return matchesCategory && matchesSearch;
  });

  // 获取复杂度颜色
  const getComplexityColor = (complexity: string) => {
    const colorMap = {
      simple: 'green',
      medium: 'orange',
      complex: 'red',
    };
    return colorMap[complexity as keyof typeof colorMap] || 'default';
  };

  return (
    <>
      <Space>
        <Button
          icon={<SaveOutlined />}
          onClick={() => setIsSaveModalVisible(true)}
          disabled={!currentWorkflow}
        >
          保存为模板
        </Button>

        <Button
          icon={<FolderOpenOutlined />}
          onClick={() => setIsModalVisible(true)}
        >
          加载模板
        </Button>

        <Upload
          accept=".json"
          showUploadList={false}
          beforeUpload={handleImportTemplate}
        >
          <Button icon={<UploadOutlined />}>
            导入模板
          </Button>
        </Upload>
      </Space>

      {/* 模板浏览器 */}
      <Modal
        title="工作流模板"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        width={900}
        footer={null}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 过滤器 */}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <Select
              value={selectedCategory}
              onChange={setSelectedCategory}
              style={{ width: 120 }}
              options={categories.map(cat => ({
                value: cat,
                label: cat === 'all' ? '全部分类' : cat
              }))}
            />

            <Input.Search
              placeholder="搜索模板..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ width: 200 }}
            />
          </div>

          <Divider style={{ margin: '12px 0' }} />

          {/* 模板列表 */}
          <List
            dataSource={filteredTemplates}
            renderItem={template => (
              <List.Item
                actions={[
                  <Button
                    type={template.isStarred ? 'primary' : 'default'}
                    icon={template.isStarred ? <StarFilled /> : <StarOutlined />}
                    onClick={() => handleToggleStar(template.id)}
                    size="small"
                  />,
                  <Button
                    icon={<CopyOutlined />}
                    onClick={() => handleCopyTemplate(template)}
                    size="small"
                  />,
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={() => handleExportTemplate(template)}
                    size="small"
                  />,
                  ...(DEFAULT_TEMPLATES.find(t => t.id === template.id) ? [] : [
                    <Popconfirm
                      title="确定删除此模板？"
                      onConfirm={() => handleDeleteTemplate(template.id)}
                    >
                      <Button
                        danger
                        icon={<DeleteOutlined />}
                        size="small"
                      />
                    </Popconfirm>
                  ]),
                  <Button
                    type="primary"
                    onClick={() => handleLoadTemplate(template)}
                    size="small"
                  >
                    加载
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      {template.name}
                      {template.isStarred && <StarFilled style={{ color: '#faad14' }} />}
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size={4}>
                      <div>{template.description}</div>
                      <Space>
                        <Tag color="blue">{template.category}</Tag>
                        <Tag color={getComplexityColor(template.metadata.complexity)}>
                          {template.metadata.complexity}
                        </Tag>
                        <Tag>{template.metadata.nodeCount} 节点</Tag>
                        <Tag>~{template.metadata.estimatedDuration}分钟</Tag>
                      </Space>
                      <Space>
                        {template.tags.map(tag => (
                          <Tag key={tag} size="small">{tag}</Tag>
                        ))}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Space>
      </Modal>

      {/* 保存模板对话框 */}
      <Modal
        title="保存工作流模板"
        open={isSaveModalVisible}
        onOk={handleSaveTemplate}
        onCancel={() => {
          setIsSaveModalVisible(false);
          form.resetFields();
        }}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="输入模板名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="模板描述"
            rules={[{ required: true, message: '请输入模板描述' }]}
          >
            <TextArea rows={3} placeholder="描述模板的功能和用途" />
          </Form.Item>

          <Form.Item
            name="category"
            label="模板分类"
            rules={[{ required: true, message: '请选择模板分类' }]}
          >
            <Select
              placeholder="选择分类"
              options={[
                { value: '文档处理', label: '文档处理' },
                { value: '代码审查', label: '代码审查' },
                { value: '数据分析', label: '数据分析' },
                { value: '内容生成', label: '内容生成' },
                { value: '自动化', label: '自动化' },
                { value: '其他', label: '其他' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="tags"
              placeholder="输入标签，支持自定义"
              options={[
                { value: 'RAG', label: 'RAG' },
                { value: '文档', label: '文档' },
                { value: '代码', label: '代码' },
                { value: '分析', label: '分析' },
                { value: '生成', label: '生成' },
                { value: '审查', label: '审查' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default WorkflowTemplateManager;
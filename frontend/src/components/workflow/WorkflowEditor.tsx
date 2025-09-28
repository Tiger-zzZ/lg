import React, { useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  ReactFlowProvider,
} from 'reactflow';
import { Card, Button, Modal, Form, Select, Input, Space, Drawer, Typography } from 'antd';
import { PlusOutlined, PlayCircleOutlined, SaveOutlined, DownloadOutlined } from '@ant-design/icons';

import AgentNode from './nodes/AgentNode';
import ConditionNode from './nodes/ConditionNode';
import MergeNode from './nodes/MergeNode';
import WorkflowToolbar from './WorkflowToolbar';
import WorkflowPanel from './WorkflowPanel';

import 'reactflow/dist/style.css';
import './WorkflowEditor.css';

const { Title } = Typography;

export interface WorkflowNode extends Node {
  type: 'agent' | 'condition' | 'merge';
  data: {
    label: string;
    agentType?: string;
    config?: any;
    status?: 'idle' | 'running' | 'completed' | 'error';
    [key: string]: any;
  };
}

export interface WorkflowEdge extends Edge {
  data?: {
    condition?: string;
    [key: string]: any;
  };
}

interface WorkflowEditorProps {
  onSave?: (workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => void;
  onExecute?: (workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => void;
  initialWorkflow?: { nodes: WorkflowNode[]; edges: WorkflowEdge[] };
}

const nodeTypes = {
  agent: AgentNode,
  condition: ConditionNode,
  merge: MergeNode,
};

const initialNodes: WorkflowNode[] = [
  {
    id: '1',
    type: 'agent',
    position: { x: 250, y: 100 },
    data: {
      label: '开始节点',
      agentType: 'research',
      status: 'idle',
    },
  },
];

const initialEdges: WorkflowEdge[] = [];

const WorkflowEditor: React.FC<WorkflowEditorProps> = ({
  onSave,
  onExecute,
  initialWorkflow,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    initialWorkflow?.nodes || initialNodes
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    initialWorkflow?.edges || initialEdges
  );

  const [isAddNodeModalVisible, setIsAddNodeModalVisible] = useState(false);
  const [selectedNodeType, setSelectedNodeType] = useState<'agent' | 'condition' | 'merge'>('agent');
  const [isConfigDrawerVisible, setIsConfigDrawerVisible] = useState(false);
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  const [form] = Form.useForm();

  // 连接处理
  const onConnect = useCallback(
    (params: Connection) => {
      const edge: WorkflowEdge = {
        ...params,
        id: `e${params.source}-${params.target}`,
        type: 'smoothstep',
        animated: true,
      };
      setEdges((eds) => addEdge(edge, eds));
    },
    [setEdges]
  );

  // 节点点击处理
  const onNodeClick = useCallback(
    (event: React.MouseEvent, node: WorkflowNode) => {
      setSelectedNode(node);
      setIsConfigDrawerVisible(true);
    },
    []
  );

  // 添加节点
  const handleAddNode = useCallback(() => {
    form.validateFields().then((values) => {
      const newNode: WorkflowNode = {
        id: `node_${Date.now()}`,
        type: selectedNodeType,
        position: {
          x: Math.random() * 500 + 100,
          y: Math.random() * 400 + 100,
        },
        data: {
          label: values.label || `新${selectedNodeType === 'agent' ? 'Agent' : selectedNodeType === 'condition' ? '条件' : '合并'}节点`,
          agentType: values.agentType,
          config: values.config,
          status: 'idle',
        },
      };

      setNodes((nds) => [...nds, newNode]);
      setIsAddNodeModalVisible(false);
      form.resetFields();
    });
  }, [selectedNodeType, form, setNodes]);

  // 删除节点
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    },
    [setNodes, setEdges]
  );

  // 更新节点配置
  const handleUpdateNode = useCallback(
    (updatedNode: WorkflowNode) => {
      setNodes((nds) =>
        nds.map((node) => (node.id === updatedNode.id ? updatedNode : node))
      );
    },
    [setNodes]
  );

  // 保存工作流
  const handleSave = useCallback(() => {
    const workflow = { nodes, edges };
    onSave?.(workflow);
  }, [nodes, edges, onSave]);

  // 执行工作流
  const handleExecute = useCallback(async () => {
    setIsExecuting(true);
    try {
      const workflow = { nodes, edges };
      await onExecute?.(workflow);
    } finally {
      setIsExecuting(false);
    }
  }, [nodes, edges, onExecute]);

  // 导出工作流
  const handleExport = useCallback(() => {
    const workflow = { nodes, edges };
    const dataStr = JSON.stringify(workflow, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `workflow_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [nodes, edges]);

  // 可用的Agent类型
  const agentTypes = [
    { value: 'research', label: '研究Agent' },
    { value: 'coding', label: '编程Agent' },
    { value: 'writing', label: '写作Agent' },
    { value: 'rag', label: 'RAG Agent' },
  ];

  return (
    <div className="workflow-editor" style={{ width: '100%', height: '100vh' }}>
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>
              工作流编辑器
            </Title>
            <Space>
              <Button
                icon={<PlusOutlined />}
                onClick={() => setIsAddNodeModalVisible(true)}
              >
                添加节点
              </Button>
              <Button
                icon={<SaveOutlined />}
                onClick={handleSave}
              >
                保存
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExport}
              >
                导出
              </Button>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={isExecuting}
                onClick={handleExecute}
              >
                执行工作流
              </Button>
            </Space>
          </div>
        }
        bodyStyle={{ padding: 0, height: 'calc(100vh - 120px)' }}
      >
        <div style={{ height: '100%', position: 'relative' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="workflow-canvas"
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>

          <WorkflowToolbar
            onAddNode={() => setIsAddNodeModalVisible(true)}
            onSave={handleSave}
            onExecute={handleExecute}
            isExecuting={isExecuting}
          />
        </div>
      </Card>

      {/* 添加节点Modal */}
      <Modal
        title="添加节点"
        open={isAddNodeModalVisible}
        onOk={handleAddNode}
        onCancel={() => {
          setIsAddNodeModalVisible(false);
          form.resetFields();
        }}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="type"
            label="节点类型"
            rules={[{ required: true, message: '请选择节点类型' }]}
          >
            <Select
              value={selectedNodeType}
              onChange={setSelectedNodeType}
              options={[
                { value: 'agent', label: 'Agent节点' },
                { value: 'condition', label: '条件节点' },
                { value: 'merge', label: '合并节点' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="label"
            label="节点名称"
            rules={[{ required: true, message: '请输入节点名称' }]}
          >
            <Input placeholder="输入节点名称" />
          </Form.Item>

          {selectedNodeType === 'agent' && (
            <Form.Item
              name="agentType"
              label="Agent类型"
              rules={[{ required: true, message: '请选择Agent类型' }]}
            >
              <Select
                placeholder="选择Agent类型"
                options={agentTypes}
              />
            </Form.Item>
          )}

          {selectedNodeType === 'condition' && (
            <Form.Item
              name="condition"
              label="条件表达式"
              rules={[{ required: true, message: '请输入条件表达式' }]}
            >
              <Input.TextArea placeholder="输入条件表达式" rows={3} />
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 节点配置抽屉 */}
      <Drawer
        title="节点配置"
        open={isConfigDrawerVisible}
        onClose={() => setIsConfigDrawerVisible(false)}
        width={400}
        extra={
          selectedNode && (
            <Button
              danger
              onClick={() => {
                if (selectedNode) {
                  handleDeleteNode(selectedNode.id);
                  setIsConfigDrawerVisible(false);
                }
              }}
            >
              删除节点
            </Button>
          )
        }
      >
        {selectedNode && (
          <WorkflowPanel
            node={selectedNode}
            onUpdate={handleUpdateNode}
            onClose={() => setIsConfigDrawerVisible(false)}
          />
        )}
      </Drawer>
    </div>
  );
};

const WorkflowEditorWrapper: React.FC<WorkflowEditorProps> = (props) => (
  <ReactFlowProvider>
    <WorkflowEditor {...props} />
  </ReactFlowProvider>
);

export default WorkflowEditorWrapper;
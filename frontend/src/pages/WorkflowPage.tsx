import React, { useState, useCallback, useEffect } from 'react';
import { Layout, Card, Row, Col, Space, Divider } from 'antd';

import WorkflowEditor from '../components/workflow/WorkflowEditor';
import WorkflowExecutor from '../components/workflow/WorkflowExecutor';
import WorkflowTemplateManager from '../components/workflow/WorkflowTemplateManager';
import type { WorkflowNode, WorkflowEdge } from '../components/workflow/WorkflowEditor';
import type { WorkflowTemplate, WorkflowExecution } from '../components/workflow/WorkflowTemplateManager';

const { Sider, Content } = Layout;

const WorkflowPage: React.FC = () => {
  const [currentWorkflow, setCurrentWorkflow] = useState<{
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
  }>({
    nodes: [],
    edges: [],
  });

  const [execution, setExecution] = useState<WorkflowExecution | null>(null);

  // 保存工作流
  const handleSaveWorkflow = useCallback((workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => {
    setCurrentWorkflow(workflow);
    console.log('工作流已保存:', workflow);
  }, []);

  // 执行工作流
  const handleExecuteWorkflow = useCallback(async (workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => {
    console.log('执行工作流:', workflow);
    // 这里应该调用后端API执行工作流
    // 暂时使用模拟实现
  }, []);

  // 加载模板
  const handleLoadTemplate = useCallback((template: WorkflowTemplate) => {
    setCurrentWorkflow({
      nodes: template.nodes,
      edges: template.edges,
    });
  }, []);

  // 节点状态变化处理
  const handleNodeStatusChange = useCallback((nodeId: string, status: WorkflowNode['data']['status']) => {
    setCurrentWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.map(node =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, status } }
          : node
      ),
    }));
  }, []);

  // 执行状态变化处理
  const handleExecutionChange = useCallback((newExecution: WorkflowExecution) => {
    setExecution(newExecution);
  }, []);

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 侧边栏 */}
      <Sider
        width={350}
        style={{
          background: 'white',
          borderRight: '1px solid #d9d9d9',
          overflow: 'auto',
        }}
      >
        <div style={{ padding: '16px' }}>
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* 模板管理 */}
            <Card title="工作流模板" size="small">
              <WorkflowTemplateManager
                currentWorkflow={currentWorkflow.nodes.length > 0 ? currentWorkflow : undefined}
                onLoadTemplate={handleLoadTemplate}
                onWorkflowChange={setCurrentWorkflow}
              />
            </Card>

            <Divider style={{ margin: '8px 0' }} />

            {/* 执行状态 */}
            <WorkflowExecutor
              workflow={currentWorkflow}
              onExecutionChange={handleExecutionChange}
              onNodeStatusChange={handleNodeStatusChange}
            />
          </Space>
        </div>
      </Sider>

      {/* 主内容区域 */}
      <Content style={{ background: 'white' }}>
        <WorkflowEditor
          onSave={handleSaveWorkflow}
          onExecute={handleExecuteWorkflow}
          initialWorkflow={currentWorkflow}
        />
      </Content>
    </Layout>
  );
};

export default WorkflowPage;
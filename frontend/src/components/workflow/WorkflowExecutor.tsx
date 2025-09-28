import React, { useState, useEffect, useCallback } from 'react';
import { Progress, Card, List, Tag, Space, Button, Modal, Descriptions } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';

import type { WorkflowNode, WorkflowEdge } from './WorkflowEditor';

export interface WorkflowExecution {
  id: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'error';
  startTime?: Date;
  endTime?: Date;
  currentNode?: string;
  progress: number;
  totalNodes: number;
  completedNodes: number;
  errorNodes: number;
  logs: ExecutionLog[];
}

export interface ExecutionLog {
  id: string;
  timestamp: Date;
  nodeId: string;
  nodeName: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
  data?: any;
}

interface WorkflowExecutorProps {
  workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] };
  onExecutionChange?: (execution: WorkflowExecution) => void;
  onNodeStatusChange?: (nodeId: string, status: WorkflowNode['data']['status']) => void;
}

const WorkflowExecutor: React.FC<WorkflowExecutorProps> = ({
  workflow,
  onExecutionChange,
  onNodeStatusChange,
}) => {
  const [execution, setExecution] = useState<WorkflowExecution>({
    id: `exec_${Date.now()}`,
    status: 'idle',
    progress: 0,
    totalNodes: workflow.nodes.length,
    completedNodes: 0,
    errorNodes: 0,
    logs: [],
  });

  const [isExecutionModalVisible, setIsExecutionModalVisible] = useState(false);

  // 添加日志
  const addLog = useCallback((log: Omit<ExecutionLog, 'id' | 'timestamp'>) => {
    const newLog: ExecutionLog = {
      id: `log_${Date.now()}_${Math.random()}`,
      timestamp: new Date(),
      ...log,
    };

    setExecution(prev => {
      const updated = {
        ...prev,
        logs: [...prev.logs, newLog],
      };
      onExecutionChange?.(updated);
      return updated;
    });
  }, [onExecutionChange]);

  // 更新节点状态
  const updateNodeStatus = useCallback((nodeId: string, status: WorkflowNode['data']['status']) => {
    onNodeStatusChange?.(nodeId, status);

    // 同步更新执行状态
    setExecution(prev => {
      let completedNodes = prev.completedNodes;
      let errorNodes = prev.errorNodes;

      if (status === 'completed') {
        completedNodes += 1;
      } else if (status === 'error') {
        errorNodes += 1;
      }

      const progress = (completedNodes / prev.totalNodes) * 100;

      const updated = {
        ...prev,
        currentNode: status === 'running' ? nodeId : prev.currentNode,
        completedNodes,
        errorNodes,
        progress,
      };
      onExecutionChange?.(updated);
      return updated;
    });
  }, [onNodeStatusChange, onExecutionChange]);

  // 模拟节点执行
  const executeNode = useCallback(async (node: WorkflowNode): Promise<boolean> => {
    updateNodeStatus(node.id, 'running');

    addLog({
      nodeId: node.id,
      nodeName: node.data.label,
      level: 'info',
      message: `开始执行节点: ${node.data.label}`,
    });

    try {
      // 模拟异步执行
      const executionTime = Math.random() * 2000 + 1000; // 1-3秒
      await new Promise(resolve => setTimeout(resolve, executionTime));

      // 模拟执行失败（10%概率）
      if (Math.random() < 0.1) {
        throw new Error('节点执行失败');
      }

      updateNodeStatus(node.id, 'completed');
      addLog({
        nodeId: node.id,
        nodeName: node.data.label,
        level: 'success',
        message: `节点执行成功: ${node.data.label}`,
        data: { executionTime: Math.round(executionTime) },
      });

      return true;
    } catch (error) {
      updateNodeStatus(node.id, 'error');
      addLog({
        nodeId: node.id,
        nodeName: node.data.label,
        level: 'error',
        message: `节点执行失败: ${node.data.label}`,
        data: { error: error instanceof Error ? error.message : '未知错误' },
      });

      return false;
    }
  }, [updateNodeStatus, addLog]);

  // 执行工作流
  const executeWorkflow = useCallback(async () => {
    setExecution(prev => ({
      ...prev,
      status: 'running',
      startTime: new Date(),
      progress: 0,
      completedNodes: 0,
      errorNodes: 0,
      logs: [],
    }));

    addLog({
      nodeId: 'system',
      nodeName: 'System',
      level: 'info',
      message: '工作流开始执行',
    });

    try {
      // 简单的顺序执行（实际应该根据边的连接关系执行）
      for (const node of workflow.nodes) {
        if (execution.status === 'paused') {
          addLog({
            nodeId: 'system',
            nodeName: 'System',
            level: 'info',
            message: '工作流执行已暂停',
          });
          return;
        }

        const success = await executeNode(node);
        if (!success) {
          // 执行失败，决定是否继续
          break;
        }
      }

      // 检查执行结果
      const hasErrors = execution.errorNodes > 0;
      const finalStatus = hasErrors ? 'error' : 'completed';

      setExecution(prev => ({
        ...prev,
        status: finalStatus,
        endTime: new Date(),
        progress: 100,
      }));

      addLog({
        nodeId: 'system',
        nodeName: 'System',
        level: hasErrors ? 'error' : 'success',
        message: hasErrors ? '工作流执行完成，但存在错误' : '工作流执行成功完成',
      });

    } catch (error) {
      setExecution(prev => ({
        ...prev,
        status: 'error',
        endTime: new Date(),
      }));

      addLog({
        nodeId: 'system',
        nodeName: 'System',
        level: 'error',
        message: '工作流执行异常终止',
        data: { error: error instanceof Error ? error.message : '未知错误' },
      });
    }
  }, [workflow.nodes, executeNode, execution.status, addLog]);

  // 暂停执行
  const pauseExecution = useCallback(() => {
    setExecution(prev => ({
      ...prev,
      status: 'paused',
    }));

    addLog({
      nodeId: 'system',
      nodeName: 'System',
      level: 'info',
      message: '工作流执行已暂停',
    });
  }, [addLog]);

  // 停止执行
  const stopExecution = useCallback(() => {
    setExecution(prev => ({
      ...prev,
      status: 'idle',
      endTime: new Date(),
    }));

    // 重置所有节点状态
    workflow.nodes.forEach(node => {
      updateNodeStatus(node.id, 'idle');
    });

    addLog({
      nodeId: 'system',
      nodeName: 'System',
      level: 'info',
      message: '工作流执行已停止',
    });
  }, [workflow.nodes, updateNodeStatus, addLog]);

  // 获取状态图标
  const getStatusIcon = (status: WorkflowExecution['status']) => {
    const iconMap = {
      idle: <ClockCircleOutlined style={{ color: '#d9d9d9' }} />,
      running: <LoadingOutlined spin style={{ color: '#1890ff' }} />,
      paused: <PauseCircleOutlined style={{ color: '#fa8c16' }} />,
      completed: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      error: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
    };
    return iconMap[status];
  };

  // 获取日志级别颜色
  const getLogLevelColor = (level: ExecutionLog['level']) => {
    const colorMap = {
      info: 'blue',
      warning: 'orange',
      error: 'red',
      success: 'green',
    };
    return colorMap[level];
  };

  return (
    <Card
      title={
        <Space>
          {getStatusIcon(execution.status)}
          工作流执行状态
        </Space>
      }
      size="small"
      extra={
        <Space>
          {execution.status === 'idle' && (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={executeWorkflow}
              size="small"
            >
              开始执行
            </Button>
          )}

          {execution.status === 'running' && (
            <>
              <Button
                icon={<PauseCircleOutlined />}
                onClick={pauseExecution}
                size="small"
              >
                暂停
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={stopExecution}
                size="small"
              >
                停止
              </Button>
            </>
          )}

          {execution.status === 'paused' && (
            <>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={executeWorkflow}
                size="small"
              >
                继续
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={stopExecution}
                size="small"
              >
                停止
              </Button>
            </>
          )}

          <Button
            onClick={() => setIsExecutionModalVisible(true)}
            size="small"
          >
            详细信息
          </Button>
        </Space>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Progress
          percent={Math.round(execution.progress)}
          status={
            execution.status === 'error'
              ? 'exception'
              : execution.status === 'completed'
              ? 'success'
              : 'active'
          }
          showInfo={true}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#666' }}>
          <span>总节点: {execution.totalNodes}</span>
          <span>已完成: {execution.completedNodes}</span>
          <span>错误: {execution.errorNodes}</span>
        </div>

        {execution.currentNode && execution.status === 'running' && (
          <div style={{ fontSize: 12, color: '#1890ff' }}>
            当前执行: {workflow.nodes.find(n => n.id === execution.currentNode)?.data.label}
          </div>
        )}
      </Space>

      {/* 详细信息弹窗 */}
      <Modal
        title="工作流执行详情"
        open={isExecutionModalVisible}
        onCancel={() => setIsExecutionModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setIsExecutionModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Descriptions column={2} size="small">
            <Descriptions.Item label="执行ID">{execution.id}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={getLogLevelColor('info')}>{execution.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {execution.startTime?.toLocaleString() || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="结束时间">
              {execution.endTime?.toLocaleString() || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="执行进度">
              {Math.round(execution.progress)}%
            </Descriptions.Item>
            <Descriptions.Item label="耗时">
              {execution.startTime && execution.endTime
                ? `${Math.round((execution.endTime.getTime() - execution.startTime.getTime()) / 1000)}秒`
                : execution.startTime
                ? `${Math.round((new Date().getTime() - execution.startTime.getTime()) / 1000)}秒`
                : '-'}
            </Descriptions.Item>
          </Descriptions>

          <Card title="执行日志" size="small">
            <List
              size="small"
              dataSource={execution.logs.slice(-10)} // 显示最近10条日志
              renderItem={log => (
                <List.Item>
                  <Space>
                    <Tag color={getLogLevelColor(log.level)} size="small">
                      {log.level}
                    </Tag>
                    <span style={{ fontSize: 12, color: '#666' }}>
                      {log.timestamp.toLocaleTimeString()}
                    </span>
                    <span style={{ fontWeight: 500 }}>{log.nodeName}:</span>
                    <span>{log.message}</span>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Space>
      </Modal>
    </Card>
  );
};

export default WorkflowExecutor;
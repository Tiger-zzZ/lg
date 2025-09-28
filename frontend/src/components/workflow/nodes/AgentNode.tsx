import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Tag, Avatar, Tooltip } from 'antd';
import {
  RobotOutlined,
  SearchOutlined,
  CodeOutlined,
  EditOutlined,
  DatabaseOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';

import type { WorkflowNode } from '../WorkflowEditor';

const AgentNode: React.FC<NodeProps<WorkflowNode>> = ({ data, selected, id }) => {
  const getAgentIcon = (agentType: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      research: <SearchOutlined />,
      coding: <CodeOutlined />,
      writing: <EditOutlined />,
      rag: <DatabaseOutlined />,
    };
    return iconMap[agentType] || <RobotOutlined />;
  };

  const getStatusIcon = (status: string) => {
    const statusIconMap: { [key: string]: React.ReactNode } = {
      idle: null,
      running: <LoadingOutlined spin />,
      completed: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
      error: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
    };
    return statusIconMap[status];
  };

  const getStatusColor = (status: string) => {
    const colorMap: { [key: string]: string } = {
      idle: 'default',
      running: 'processing',
      completed: 'success',
      error: 'error',
    };
    return colorMap[status] || 'default';
  };

  const statusIcon = getStatusIcon(data.status || 'idle');
  const agentIcon = getAgentIcon(data.agentType || 'research');

  return (
    <div className={`agent-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#1890ff' }}
      />

      <Card
        size="small"
        style={{
          width: 200,
          minHeight: 80,
          border: selected ? '2px solid #1890ff' : '1px solid #d9d9d9',
          boxShadow: selected ? '0 0 10px rgba(24, 144, 255, 0.3)' : undefined,
        }}
        bodyStyle={{ padding: '12px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <Avatar
            size="small"
            icon={agentIcon}
            style={{ backgroundColor: '#1890ff', marginRight: 8 }}
          />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                fontSize: 14,
                fontWeight: 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {data.label}
            </div>
          </div>
          {statusIcon && (
            <Tooltip title={`状态: ${data.status}`}>
              {statusIcon}
            </Tooltip>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Tag size="small" color="blue">
            {data.agentType || 'agent'}
          </Tag>
          <Tag size="small" color={getStatusColor(data.status || 'idle')}>
            {data.status || 'idle'}
          </Tag>
        </div>

        {data.config && (
          <div style={{ fontSize: 12, color: '#666', marginTop: 8, textAlign: 'center' }}>
            已配置
          </div>
        )}
      </Card>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#1890ff' }}
      />
    </div>
  );
};

export default AgentNode;
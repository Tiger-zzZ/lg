import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Tag, Avatar } from 'antd';
import { BranchesOutlined } from '@ant-design/icons';

import type { WorkflowNode } from '../WorkflowEditor';

const ConditionNode: React.FC<NodeProps<WorkflowNode>> = ({ data, selected }) => {
  return (
    <div className={`condition-node ${selected ? 'selected' : ''}`}>
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#fa8c16' }}
      />

      <Card
        size="small"
        style={{
          width: 180,
          minHeight: 80,
          border: selected ? '2px solid #fa8c16' : '1px solid #d9d9d9',
          boxShadow: selected ? '0 0 10px rgba(250, 140, 22, 0.3)' : undefined,
        }}
        bodyStyle={{ padding: '12px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <Avatar
            size="small"
            icon={<BranchesOutlined />}
            style={{ backgroundColor: '#fa8c16', marginRight: 8 }}
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
        </div>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <Tag size="small" color="orange">
            条件判断
          </Tag>
        </div>

        {data.condition && (
          <div
            style={{
              fontSize: 11,
              color: '#666',
              marginTop: 6,
              textAlign: 'center',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {data.condition}
          </div>
        )}
      </Card>

      {/* 条件节点通常有多个输出 */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="true"
        style={{ background: '#52c41a', left: '25%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="false"
        style={{ background: '#ff4d4f', left: '75%' }}
      />
    </div>
  );
};

export default ConditionNode;
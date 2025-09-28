import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, Tag, Avatar } from 'antd';
import { MergeOutlined } from '@ant-design/icons';

import type { WorkflowNode } from '../WorkflowEditor';

const MergeNode: React.FC<NodeProps<WorkflowNode>> = ({ data, selected }) => {
  return (
    <div className={`merge-node ${selected ? 'selected' : ''}`}>
      {/* 合并节点通常有多个输入 */}
      <Handle
        type="target"
        position={Position.Top}
        id="input1"
        style={{ background: '#722ed1', left: '25%' }}
      />
      <Handle
        type="target"
        position={Position.Top}
        id="input2"
        style={{ background: '#722ed1', left: '75%' }}
      />

      <Card
        size="small"
        style={{
          width: 160,
          minHeight: 80,
          border: selected ? '2px solid #722ed1' : '1px solid #d9d9d9',
          boxShadow: selected ? '0 0 10px rgba(114, 46, 209, 0.3)' : undefined,
        }}
        bodyStyle={{ padding: '12px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
          <Avatar
            size="small"
            icon={<MergeOutlined />}
            style={{ backgroundColor: '#722ed1', marginRight: 8 }}
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
          <Tag size="small" color="purple">
            合并节点
          </Tag>
        </div>

        {data.mergeStrategy && (
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
            {data.mergeStrategy}
          </div>
        )}
      </Card>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#722ed1' }}
      />
    </div>
  );
};

export default MergeNode;
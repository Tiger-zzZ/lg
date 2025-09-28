import React from 'react';
import { Button, Space, Tooltip } from 'antd';
import {
  PlusOutlined,
  SaveOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons';

interface WorkflowToolbarProps {
  onAddNode: () => void;
  onSave: () => void;
  onExecute: () => void;
  onPause?: () => void;
  onReset?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onFitView?: () => void;
  isExecuting?: boolean;
  isPaused?: boolean;
}

const WorkflowToolbar: React.FC<WorkflowToolbarProps> = ({
  onAddNode,
  onSave,
  onExecute,
  onPause,
  onReset,
  onZoomIn,
  onZoomOut,
  onFitView,
  isExecuting = false,
  isPaused = false,
}) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: 16,
        zIndex: 10,
        background: 'white',
        borderRadius: 8,
        padding: '8px 12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        border: '1px solid #d9d9d9',
      }}
    >
      <Space>
        <Tooltip title="添加节点">
          <Button
            type="default"
            icon={<PlusOutlined />}
            onClick={onAddNode}
            size="small"
          >
            添加节点
          </Button>
        </Tooltip>

        <div style={{ width: 1, height: 20, background: '#d9d9d9' }} />

        <Tooltip title="保存工作流">
          <Button
            icon={<SaveOutlined />}
            onClick={onSave}
            size="small"
          >
            保存
          </Button>
        </Tooltip>

        <Tooltip title={isExecuting ? '暂停执行' : '执行工作流'}>
          <Button
            type={isExecuting ? 'default' : 'primary'}
            icon={isExecuting ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={isExecuting ? onPause : onExecute}
            loading={isExecuting}
            size="small"
          >
            {isExecuting ? '暂停' : '执行'}
          </Button>
        </Tooltip>

        {onReset && (
          <Tooltip title="重置工作流">
            <Button
              icon={<ReloadOutlined />}
              onClick={onReset}
              size="small"
              disabled={isExecuting}
            >
              重置
            </Button>
          </Tooltip>
        )}

        <div style={{ width: 1, height: 20, background: '#d9d9d9' }} />

        {onZoomIn && (
          <Tooltip title="放大">
            <Button
              icon={<ZoomInOutlined />}
              onClick={onZoomIn}
              size="small"
            />
          </Tooltip>
        )}

        {onZoomOut && (
          <Tooltip title="缩小">
            <Button
              icon={<ZoomOutOutlined />}
              onClick={onZoomOut}
              size="small"
            />
          </Tooltip>
        )}

        {onFitView && (
          <Tooltip title="适应画布">
            <Button
              icon={<FullscreenOutlined />}
              onClick={onFitView}
              size="small"
            />
          </Tooltip>
        )}
      </Space>
    </div>
  );
};

export default WorkflowToolbar;
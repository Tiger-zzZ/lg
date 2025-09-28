import React from 'react';
import { Card, Button, Empty, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

const { Title } = Typography;

const AgentPage: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          🤖 Agent管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          创建Agent
        </Button>
      </div>

      <Card>
        <Empty
          description="暂无Agent，点击上方按钮创建第一个Agent"
          image="/api/placeholder/400/300"
        />
      </Card>
    </div>
  );
};

export default AgentPage;
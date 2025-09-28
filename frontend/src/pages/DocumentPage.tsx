import React from 'react';
import { Card, Button, Empty, Typography, Upload } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const { Title } = Typography;
const { Dragger } = Upload;

const DocumentPage: React.FC = () => {
  const uploadProps = {
    name: 'file',
    action: '/api/v1/documents/upload',
    accept: '.pdf,.docx,.txt,.md',
    onChange: (info: any) => {
      console.log('Upload info:', info);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          📚 文档管理
        </Title>
        <Button type="primary" icon={<UploadOutlined />}>
          上传文档
        </Button>
      </div>

      <Card title="文档上传" style={{ marginBottom: 24 }}>
        <Dragger {...uploadProps}>
          <p style={{ fontSize: 48 }}>📁</p>
          <p>点击或拖拽文件到此区域上传</p>
          <p style={{ color: '#999' }}>
            支持 PDF, DOCX, TXT, MD 格式文件
          </p>
        </Dragger>
      </Card>

      <Card title="我的文档">
        <Empty
          description="暂无文档，上传第一个文档开始使用RAG功能"
          image="/api/placeholder/400/300"
        />
      </Card>
    </div>
  );
};

export default DocumentPage;
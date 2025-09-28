# 前端组件结构设计

## 整体架构

```
src/
├── components/           # 可复用组件
│   ├── common/          # 通用组件
│   ├── forms/           # 表单组件
│   ├── layout/          # 布局组件
│   └── charts/          # 图表组件
├── pages/               # 页面组件
├── stores/              # Zustand状态管理
├── services/            # API服务
├── types/               # TypeScript类型
├── hooks/               # 自定义Hook
├── utils/               # 工具函数
├── constants/           # 常量定义
└── assets/              # 静态资源
```

## 核心页面组件

### 1. 认证页面 (pages/auth/)
```typescript
// pages/auth/LoginPage.tsx
interface LoginPageProps {}
export const LoginPage: React.FC<LoginPageProps>

// pages/auth/RegisterPage.tsx
export const RegisterPage: React.FC
```

### 2. 主仪表板 (pages/dashboard/)
```typescript
// pages/dashboard/DashboardPage.tsx
interface DashboardStats {
  totalAgents: number;
  activeWorkflows: number;
  totalDocuments: number;
  systemStatus: 'healthy' | 'warning' | 'error';
}

export const DashboardPage: React.FC
```

### 3. Agent管理 (pages/agents/)
```typescript
// pages/agents/AgentListPage.tsx
export const AgentListPage: React.FC

// pages/agents/AgentDetailPage.tsx
interface AgentDetailPageProps {
  agentId: string;
}
export const AgentDetailPage: React.FC<AgentDetailPageProps>

// pages/agents/CreateAgentPage.tsx
export const CreateAgentPage: React.FC
```

### 4. 工作流管理 (pages/workflows/)
```typescript
// pages/workflows/WorkflowListPage.tsx
export const WorkflowListPage: React.FC

// pages/workflows/WorkflowEditorPage.tsx
interface WorkflowEditorPageProps {
  workflowId?: string;
}
export const WorkflowEditorPage: React.FC<WorkflowEditorPageProps>

// pages/workflows/WorkflowExecutionPage.tsx
export const WorkflowExecutionPage: React.FC
```

### 5. 对话界面 (pages/chat/)
```typescript
// pages/chat/ChatPage.tsx
interface ChatPageProps {
  sessionId?: string;
}
export const ChatPage: React.FC<ChatPageProps>
```

### 6. 文档管理 (pages/documents/)
```typescript
// pages/documents/DocumentListPage.tsx
export const DocumentListPage: React.FC

// pages/documents/DocumentUploadPage.tsx
export const DocumentUploadPage: React.FC

// pages/documents/DocumentViewerPage.tsx
export const DocumentViewerPage: React.FC
```

## 核心可复用组件

### 1. 布局组件 (components/layout/)

#### MainLayout
```typescript
// components/layout/MainLayout.tsx
interface MainLayoutProps {
  children: React.ReactNode;
  sidebarCollapsed?: boolean;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, sidebarCollapsed = false }) => {
  return (
    <Layout>
      <Sidebar collapsed={sidebarCollapsed} />
      <Layout>
        <Header />
        <Content>{children}</Content>
      </Layout>
    </Layout>
  );
};
```

#### Sidebar
```typescript
// components/layout/Sidebar.tsx
interface SidebarProps {
  collapsed: boolean;
}

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
  children?: MenuItem[];
}

export const Sidebar: React.FC<SidebarProps>
```

#### Header
```typescript
// components/layout/Header.tsx
export const Header: React.FC = () => {
  const { user, logout } = useAuthStore();

  return (
    <AntdHeader>
      <div className="header-left">
        <Breadcrumb />
      </div>
      <div className="header-right">
        <NotificationBell />
        <UserMenu user={user} onLogout={logout} />
      </div>
    </AntdHeader>
  );
};
```

### 2. Agent相关组件 (components/agents/)

#### AgentCard
```typescript
// components/agents/AgentCard.tsx
interface AgentCardProps {
  agent: Agent;
  onEdit: (agent: Agent) => void;
  onDelete: (agentId: string) => void;
  onStart: (agentId: string) => void;
  onStop: (agentId: string) => void;
}

export const AgentCard: React.FC<AgentCardProps>
```

#### AgentForm
```typescript
// components/agents/AgentForm.tsx
interface AgentFormProps {
  initialValues?: Partial<Agent>;
  onSubmit: (values: CreateAgentRequest) => void;
  onCancel: () => void;
  loading?: boolean;
}

export const AgentForm: React.FC<AgentFormProps>
```

#### AgentStatus
```typescript
// components/agents/AgentStatus.tsx
interface AgentStatusProps {
  status: AgentStatus;
  size?: 'small' | 'default' | 'large';
}

export const AgentStatus: React.FC<AgentStatusProps>
```

### 3. 工作流组件 (components/workflows/)

#### WorkflowCanvas
```typescript
// components/workflows/WorkflowCanvas.tsx
interface WorkflowCanvasProps {
  workflow: Workflow;
  onChange: (workflow: Workflow) => void;
  readonly?: boolean;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps>
```

#### WorkflowNode
```typescript
// components/workflows/WorkflowNode.tsx
interface WorkflowNodeProps {
  node: WorkflowNode;
  onEdit: (node: WorkflowNode) => void;
  onDelete: (nodeId: string) => void;
  selected?: boolean;
}

export const WorkflowNode: React.FC<WorkflowNodeProps>
```

### 4. 对话组件 (components/chat/)

#### ChatInterface
```typescript
// components/chat/ChatInterface.tsx
interface ChatInterfaceProps {
  sessionId: string;
  onMessageSend: (message: string) => void;
  messages: ChatMessage[];
  loading?: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps>
```

#### MessageBubble
```typescript
// components/chat/MessageBubble.tsx
interface MessageBubbleProps {
  message: ChatMessage;
  showAvatar?: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps>
```

#### MessageInput
```typescript
// components/chat/MessageInput.tsx
interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const MessageInput: React.FC<MessageInputProps>
```

### 5. 文档组件 (components/documents/)

#### DocumentUploader
```typescript
// components/documents/DocumentUploader.tsx
interface DocumentUploaderProps {
  onUpload: (files: File[]) => void;
  accept?: string[];
  maxSize?: number;
  multiple?: boolean;
}

export const DocumentUploader: React.FC<DocumentUploaderProps>
```

#### DocumentCard
```typescript
// components/documents/DocumentCard.tsx
interface DocumentCardProps {
  document: Document;
  onView: (document: Document) => void;
  onDelete: (documentId: string) => void;
  onDownload: (document: Document) => void;
}

export const DocumentCard: React.FC<DocumentCardProps>
```

### 6. 通用组件 (components/common/)

#### LoadingSpinner
```typescript
// components/common/LoadingSpinner.tsx
interface LoadingSpinnerProps {
  size?: 'small' | 'default' | 'large';
  message?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps>
```

#### ErrorBoundary
```typescript
// components/common/ErrorBoundary.tsx
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const ErrorBoundary: React.FC<ErrorBoundaryProps>
```

#### ConfirmDialog
```typescript
// components/common/ConfirmDialog.tsx
interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps>
```

## 状态管理结构 (stores/)

### 1. 认证状态
```typescript
// stores/useAuthStore.ts
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
  register: (userData: RegisterRequest) => Promise<void>;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState & AuthActions>()
```

### 2. Agent状态
```typescript
// stores/useAgentStore.ts
interface AgentState {
  agents: Agent[];
  selectedAgent: Agent | null;
  loading: boolean;
  error: string | null;
}

interface AgentActions {
  fetchAgents: () => Promise<void>;
  createAgent: (agent: CreateAgentRequest) => Promise<void>;
  updateAgent: (id: string, agent: UpdateAgentRequest) => Promise<void>;
  deleteAgent: (id: string) => Promise<void>;
  startAgent: (id: string) => Promise<void>;
  stopAgent: (id: string) => Promise<void>;
}

export const useAgentStore = create<AgentState & AgentActions>()
```

### 3. 工作流状态
```typescript
// stores/useWorkflowStore.ts
interface WorkflowState {
  workflows: Workflow[];
  currentWorkflow: Workflow | null;
  executions: WorkflowExecution[];
  loading: boolean;
}

export const useWorkflowStore = create<WorkflowState & WorkflowActions>()
```

### 4. 对话状态
```typescript
// stores/useChatStore.ts
interface ChatState {
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  loading: boolean;
}

export const useChatStore = create<ChatState & ChatActions>()
```

## 自定义Hooks (hooks/)

### 1. API相关Hooks
```typescript
// hooks/useApi.ts
export const useApi = <T>(apiCall: () => Promise<T>) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async () => {
    // 实现逻辑
  }, [apiCall]);

  return { data, loading, error, execute };
};
```

### 2. WebSocket Hooks
```typescript
// hooks/useWebSocket.ts
export const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);

  // WebSocket连接逻辑

  return { socket, connected, emit: socket?.emit, on: socket?.on };
};
```

### 3. 实时数据Hooks
```typescript
// hooks/useRealTimeData.ts
export const useRealTimeData = <T>(endpoint: string, interval = 5000) => {
  const [data, setData] = useState<T | null>(null);

  useEffect(() => {
    // 轮询或WebSocket实时数据更新
  }, [endpoint, interval]);

  return data;
};
```

## 路由配置

### 主路由结构
```typescript
// App.tsx
const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "agents", element: <AgentListPage /> },
      { path: "agents/create", element: <CreateAgentPage /> },
      { path: "agents/:id", element: <AgentDetailPage /> },
      { path: "workflows", element: <WorkflowListPage /> },
      { path: "workflows/create", element: <WorkflowEditorPage /> },
      { path: "workflows/:id", element: <WorkflowEditorPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "chat/:sessionId", element: <ChatPage /> },
      { path: "documents", element: <DocumentListPage /> },
      { path: "documents/upload", element: <DocumentUploadPage /> },
    ]
  },
  {
    path: "/auth",
    children: [
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> }
    ]
  }
]);
```

## 样式和主题

### 1. 全局样式
```css
/* styles/globals.css */
:root {
  --primary-color: #1890ff;
  --success-color: #52c41a;
  --warning-color: #faad14;
  --error-color: #f5222d;
  --text-color: #000000d9;
  --text-secondary: #00000073;
  --border-color: #d9d9d9;
  --background-color: #f0f2f5;
}
```

### 2. 组件样式
```typescript
// 使用CSS-in-JS或styled-components
import styled from '@emotion/styled';

export const StyledAgentCard = styled.div`
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.3s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
`;
```

这个前端组件结构设计考虑了现代React应用的最佳实践，包括组件复用、状态管理、类型安全和用户体验优化。所有组件都使用TypeScript进行强类型约束，确保代码的可维护性和健壮性。
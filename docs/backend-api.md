# 后端API设计

## API架构概述

基于FastAPI的RESTful API设计，支持异步处理和WebSocket实时通信。

### 基础URL结构
```
https://api.lg-platform.com/api/v1/
```

### 通用响应格式
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: string[];
  meta?: {
    pagination?: PaginationMeta;
    timestamp: string;
    requestId: string;
  };
}

interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
```

## 1. 认证和授权 API

### 基础路径: `/api/v1/auth`

#### POST /auth/register
用户注册
```typescript
// Request
interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  firstName: string;
  lastName: string;
}

// Response
interface RegisterResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
}
```

#### POST /auth/login
用户登录
```typescript
// Request
interface LoginRequest {
  email: string;
  password: string;
}

// Response
interface LoginResponse {
  user: User;
  accessToken: string;
  refreshToken: string;
}
```

#### POST /auth/refresh
刷新访问令牌
```typescript
// Request
interface RefreshRequest {
  refreshToken: string;
}

// Response
interface RefreshResponse {
  accessToken: string;
  refreshToken: string;
}
```

#### POST /auth/logout
用户登出
```typescript
// Request
interface LogoutRequest {
  refreshToken: string;
}

// Response: 204 No Content
```

#### GET /auth/me
获取当前用户信息
```typescript
// Response
interface CurrentUserResponse {
  user: User;
  permissions: string[];
}
```

## 2. 用户管理 API

### 基础路径: `/api/v1/users`

#### GET /users
获取用户列表（管理员权限）
```typescript
// Query Parameters
interface GetUsersQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  role?: UserRole;
}

// Response
interface GetUsersResponse {
  users: User[];
  meta: PaginationMeta;
}
```

#### GET /users/{userId}
获取用户详情
```typescript
// Response
interface GetUserResponse {
  user: User;
}
```

#### PUT /users/{userId}
更新用户信息
```typescript
// Request
interface UpdateUserRequest {
  firstName?: string;
  lastName?: string;
  email?: string;
  role?: UserRole;
  isActive?: boolean;
}

// Response
interface UpdateUserResponse {
  user: User;
}
```

## 3. Agent管理 API

### 基础路径: `/api/v1/agents`

#### GET /agents
获取Agent列表
```typescript
// Query Parameters
interface GetAgentsQuery {
  page?: number;
  pageSize?: number;
  type?: AgentType;
  status?: AgentStatus;
  search?: string;
}

// Response
interface GetAgentsResponse {
  agents: Agent[];
  meta: PaginationMeta;
}
```

#### POST /agents
创建新Agent
```typescript
// Request
interface CreateAgentRequest {
  name: string;
  description: string;
  type: AgentType;
  config: AgentConfig;
  tools: string[];
  model: LLMModel;
}

// Response
interface CreateAgentResponse {
  agent: Agent;
}
```

#### GET /agents/{agentId}
获取Agent详情
```typescript
// Response
interface GetAgentResponse {
  agent: Agent;
  stats: AgentStats;
  recentExecutions: AgentExecution[];
}
```

#### PUT /agents/{agentId}
更新Agent
```typescript
// Request
interface UpdateAgentRequest {
  name?: string;
  description?: string;
  config?: AgentConfig;
  tools?: string[];
  model?: LLMModel;
}

// Response
interface UpdateAgentResponse {
  agent: Agent;
}
```

#### DELETE /agents/{agentId}
删除Agent
```typescript
// Response: 204 No Content
```

#### POST /agents/{agentId}/start
启动Agent
```typescript
// Response
interface StartAgentResponse {
  agent: Agent;
  taskId: string;
}
```

#### POST /agents/{agentId}/stop
停止Agent
```typescript
// Response
interface StopAgentResponse {
  agent: Agent;
}
```

#### GET /agents/{agentId}/executions
获取Agent执行历史
```typescript
// Query Parameters
interface GetAgentExecutionsQuery {
  page?: number;
  pageSize?: number;
  status?: ExecutionStatus;
  startDate?: string;
  endDate?: string;
}

// Response
interface GetAgentExecutionsResponse {
  executions: AgentExecution[];
  meta: PaginationMeta;
}
```

## 4. 工作流管理 API

### 基础路径: `/api/v1/workflows`

#### GET /workflows
获取工作流列表
```typescript
// Query Parameters
interface GetWorkflowsQuery {
  page?: number;
  pageSize?: number;
  status?: WorkflowStatus;
  search?: string;
}

// Response
interface GetWorkflowsResponse {
  workflows: Workflow[];
  meta: PaginationMeta;
}
```

#### POST /workflows
创建工作流
```typescript
// Request
interface CreateWorkflowRequest {
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  config: WorkflowConfig;
}

// Response
interface CreateWorkflowResponse {
  workflow: Workflow;
}
```

#### GET /workflows/{workflowId}
获取工作流详情
```typescript
// Response
interface GetWorkflowResponse {
  workflow: Workflow;
  stats: WorkflowStats;
}
```

#### PUT /workflows/{workflowId}
更新工作流
```typescript
// Request
interface UpdateWorkflowRequest {
  name?: string;
  description?: string;
  nodes?: WorkflowNode[];
  edges?: WorkflowEdge[];
  config?: WorkflowConfig;
}

// Response
interface UpdateWorkflowResponse {
  workflow: Workflow;
}
```

#### POST /workflows/{workflowId}/execute
执行工作流
```typescript
// Request
interface ExecuteWorkflowRequest {
  inputs?: Record<string, any>;
  config?: ExecutionConfig;
}

// Response
interface ExecuteWorkflowResponse {
  execution: WorkflowExecution;
}
```

#### GET /workflows/{workflowId}/executions
获取工作流执行历史
```typescript
// Response
interface GetWorkflowExecutionsResponse {
  executions: WorkflowExecution[];
  meta: PaginationMeta;
}
```

## 5. 对话管理 API

### 基础路径: `/api/v1/chat`

#### GET /chat/sessions
获取对话会话列表
```typescript
// Response
interface GetChatSessionsResponse {
  sessions: ChatSession[];
  meta: PaginationMeta;
}
```

#### POST /chat/sessions
创建新对话会话
```typescript
// Request
interface CreateChatSessionRequest {
  name?: string;
  agentId?: string;
  workflowId?: string;
}

// Response
interface CreateChatSessionResponse {
  session: ChatSession;
}
```

#### GET /chat/sessions/{sessionId}
获取会话详情和消息历史
```typescript
// Response
interface GetChatSessionResponse {
  session: ChatSession;
  messages: ChatMessage[];
}
```

#### POST /chat/sessions/{sessionId}/messages
发送消息
```typescript
// Request
interface SendMessageRequest {
  content: string;
  attachments?: MessageAttachment[];
}

// Response
interface SendMessageResponse {
  message: ChatMessage;
  response: ChatMessage;
}
```

#### DELETE /chat/sessions/{sessionId}
删除会话
```typescript
// Response: 204 No Content
```

## 6. 文档管理 API

### 基础路径: `/api/v1/documents`

#### GET /documents
获取文档列表
```typescript
// Query Parameters
interface GetDocumentsQuery {
  page?: number;
  pageSize?: number;
  type?: DocumentType;
  search?: string;
  folderId?: string;
}

// Response
interface GetDocumentsResponse {
  documents: Document[];
  meta: PaginationMeta;
}
```

#### POST /documents/upload
上传文档
```typescript
// Request: multipart/form-data
// file: File
// metadata: {
//   name?: string;
//   description?: string;
//   folderId?: string;
//   tags?: string[];
// }

// Response
interface UploadDocumentResponse {
  document: Document;
  processingTaskId: string;
}
```

#### GET /documents/{documentId}
获取文档详情
```typescript
// Response
interface GetDocumentResponse {
  document: Document;
  chunks?: DocumentChunk[];
}
```

#### PUT /documents/{documentId}
更新文档元数据
```typescript
// Request
interface UpdateDocumentRequest {
  name?: string;
  description?: string;
  tags?: string[];
}

// Response
interface UpdateDocumentResponse {
  document: Document;
}
```

#### DELETE /documents/{documentId}
删除文档
```typescript
// Response: 204 No Content
```

#### POST /documents/{documentId}/reprocess
重新处理文档
```typescript
// Response
interface ReprocessDocumentResponse {
  taskId: string;
}
```

## 7. RAG系统 API

### 基础路径: `/api/v1/rag`

#### POST /rag/search
执行语义搜索
```typescript
// Request
interface SemanticSearchRequest {
  query: string;
  limit?: number;
  threshold?: number;
  filters?: Record<string, any>;
  documentIds?: string[];
}

// Response
interface SemanticSearchResponse {
  results: SearchResult[];
  totalResults: number;
  searchTime: number;
}
```

#### POST /rag/query
执行RAG查询
```typescript
// Request
interface RAGQueryRequest {
  query: string;
  sessionId?: string;
  config?: RAGConfig;
}

// Response
interface RAGQueryResponse {
  answer: string;
  sources: DocumentChunk[];
  confidence: number;
  processingTime: number;
}
```

#### GET /rag/stats
获取RAG系统统计
```typescript
// Response
interface RAGStatsResponse {
  totalDocuments: number;
  totalChunks: number;
  indexSize: number;
  lastIndexUpdate: string;
}
```

## 8. 系统管理 API

### 基础路径: `/api/v1/admin`

#### GET /admin/stats
获取系统统计信息
```typescript
// Response
interface SystemStatsResponse {
  users: {
    total: number;
    active: number;
    newThisWeek: number;
  };
  agents: {
    total: number;
    active: number;
    idle: number;
  };
  executions: {
    today: number;
    thisWeek: number;
    thisMonth: number;
  };
  storage: {
    used: number;
    total: number;
    documents: number;
  };
}
```

#### GET /admin/health
系统健康检查
```typescript
// Response
interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    vectorDb: ServiceStatus;
    celery: ServiceStatus;
  };
  version: string;
  uptime: number;
}
```

#### GET /admin/logs
获取系统日志
```typescript
// Query Parameters
interface GetLogsQuery {
  level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  service?: string;
  startTime?: string;
  endTime?: string;
  limit?: number;
}

// Response
interface GetLogsResponse {
  logs: LogEntry[];
  meta: PaginationMeta;
}
```

## 9. WebSocket API

### 连接端点: `/ws`

#### 连接认证
```typescript
// Connection query parameters
interface WSConnectionParams {
  token: string;  // JWT token
  userId: string;
}
```

#### 消息格式
```typescript
interface WSMessage {
  type: WSMessageType;
  payload: any;
  messageId: string;
  timestamp: string;
}

enum WSMessageType {
  // Agent events
  AGENT_STATUS_CHANGED = 'agent_status_changed',
  AGENT_EXECUTION_STARTED = 'agent_execution_started',
  AGENT_EXECUTION_COMPLETED = 'agent_execution_completed',

  // Chat events
  NEW_MESSAGE = 'new_message',
  TYPING_START = 'typing_start',
  TYPING_END = 'typing_end',

  // Workflow events
  WORKFLOW_EXECUTION_STARTED = 'workflow_execution_started',
  WORKFLOW_EXECUTION_COMPLETED = 'workflow_execution_completed',
  WORKFLOW_NODE_COMPLETED = 'workflow_node_completed',

  // System events
  SYSTEM_NOTIFICATION = 'system_notification',

  // Client events
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',
  HEARTBEAT = 'heartbeat',
}
```

#### 订阅频道
```typescript
// Subscribe to specific events
interface SubscribeMessage {
  type: 'subscribe';
  payload: {
    channels: string[];  // e.g., ['agent:123', 'chat:456', 'user:789']
  };
}
```

## 错误处理

### HTTP状态码规范
- 200: 成功
- 201: 创建成功
- 204: 无内容（删除成功）
- 400: 请求错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 409: 资源冲突
- 422: 验证错误
- 429: 请求过于频繁
- 500: 服务器内部错误

### 错误响应格式
```typescript
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
  };
  meta: {
    timestamp: string;
    requestId: string;
    path: string;
  };
}
```

## API版本控制

### 版本策略
- URL路径版本控制: `/api/v1/`, `/api/v2/`
- 向后兼容性保证
- 弃用通知机制

### 响应头
```
X-API-Version: v1
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## 安全和限制

### 认证方式
- JWT Bearer Token
- API Key (for service-to-service)

### 限流策略
- 用户级别: 1000 requests/hour
- IP级别: 100 requests/minute
- API Key级别: 10000 requests/hour

### 数据验证
- 输入数据验证使用Pydantic
- SQL注入防护
- XSS防护
- CSRF保护

这个API设计提供了完整的RESTful接口和WebSocket实时通信支持，满足多Agent平台的所有核心功能需求。
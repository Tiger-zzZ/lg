# 技术栈和依赖清单

## 后端依赖 (UV管理)

### pyproject.toml 配置
```toml
[project]
name = "lg-backend"
version = "0.1.0"
description = "LangGraph Multi-Agent Platform Backend"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
readme = "README.md"
requires-python = ">=3.11"

dependencies = [
    # Web框架
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "gunicorn>=21.2.0",

    # LangChain生态
    "langgraph>=0.2.0",
    "langchain>=0.1.0",
    "langchain-community>=0.0.10",
    "langchain-openai>=0.0.5",
    "langchain-chroma>=0.1.0",

    # 数据库
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "psycopg2-binary>=2.9.0",
    "redis>=5.0.0",

    # 向量数据库
    "chromadb>=0.4.0",
    "sentence-transformers>=2.2.0",

    # 认证和安全
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.0",
    "python-multipart>=0.0.6",

    # 异步处理
    "celery[redis]>=5.3.0",
    "flower>=2.0.0",

    # 文档处理
    "python-docx>=1.1.0",
    "PyPDF2>=3.0.0",
    "openpyxl>=3.1.0",
    "python-magic>=0.4.0",

    # 实用工具
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "tenacity>=8.2.0",
    "httpx>=0.25.0",

    # 监控和日志
    "prometheus-client>=0.18.0",
    "structlog>=23.1.0",
    "python-json-logger>=2.0.0",

    # WebSocket支持
    "python-socketio>=5.9.0",
    "websockets>=11.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
    "httpx>=0.25.0",  # for testing
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.7.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
```

## 前端依赖 (npm/pnpm)

### package.json
```json
{
  "name": "lg-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.15.0",
    "axios": "^1.5.0",
    "zustand": "^4.4.0",
    "@ant-design/icons": "^5.2.0",
    "antd": "^5.9.0",
    "socket.io-client": "^4.7.0",
    "@monaco-editor/react": "^4.6.0",
    "react-flow-renderer": "^10.3.0",
    "recharts": "^2.8.0",
    "dayjs": "^1.11.0",
    "react-markdown": "^9.0.0",
    "react-syntax-highlighter": "^15.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@vitejs/plugin-react": "^4.0.3",
    "eslint": "^8.45.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.3",
    "typescript": "^5.0.2",
    "vite": "^4.4.5",
    "@types/react-syntax-highlighter": "^15.5.0"
  }
}
```

## Docker和基础设施

### docker-compose.yml 主要服务
```yaml
version: '3.8'

services:
  # 数据库服务
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: lg_platform
      POSTGRES_USER: lg_user
      POSTGRES_PASSWORD: lg_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6378:6379"
    volumes:
      - redis_data:/data

  # 向量数据库
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/chroma/chroma

  # 消息队列
  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: lg_user
      RABBITMQ_DEFAULT_PASS: lg_password
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  postgres_data:
  redis_data:
  chroma_data:
  rabbitmq_data:
```

## 开发工具配置

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## 环境变量配置

### .env.example
```bash
# 数据库配置
DATABASE_URL=postgresql://lg_user:lg_password@localhost:5432/lg_platform
REDIS_URL=redis://localhost:6378/0

# LLM配置
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# JWT配置
SECRET_KEY=your_super_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Chroma配置
CHROMA_HOST=localhost
CHROMA_PORT=8000

# 应用配置
DEBUG=true
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Celery配置
CELERY_BROKER_URL=redis://localhost:6378/1
CELERY_RESULT_BACKEND=redis://localhost:6378/1
```

## 部署依赖

### Kubernetes (可选)
```yaml
# kubernetes/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lg-platform
```

### Nginx配置
```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name localhost;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 推荐的开发工具

### VS Code扩展
- Python
- Pylance
- Black Formatter
- ES7+ React/Redux/React-Native snippets
- TypeScript Importer
- Thunder Client (API测试)
- Docker

### 命令行工具
```bash
# 安装UV (Python包管理器)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装Node.js (推荐使用fnm)
fnm use 20

# 安装pnpm (可选，比npm更快)
npm install -g pnpm
```

## 性能和监控工具

### APM工具
- Prometheus + Grafana
- Sentry (错误监控)
- New Relic (可选)

### 数据库监控
- pgAdmin (PostgreSQL管理)
- RedisInsight (Redis管理)

这个技术栈配置考虑了现代Python和React开发的最佳实践，同时确保了与LangGraph和RAG系统的良好集成。UV作为Python包管理器提供了更快的依赖解析和安装速度。
# LG Platform Backend

基于FastAPI + LangGraph的多Agent平台后端服务

## 快速开始

### 1. 安装UV (Python包管理器)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 安装依赖
```bash
uv sync
```

### 3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置数据库连接和API密钥
```

### 4. 启动数据库服务
```bash
# 在项目根目录运行
docker-compose up -d postgres redis chroma
```

### 5. 运行数据库迁移
```bash
uv run alembic upgrade head
```

### 6. 启动开发服务器
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要功能

- ✅ 用户认证系统 (JWT)
- ✅ 基础Agent框架 (LangGraph)
- ✅ 健康检查和监控
- ⏳ RAG文档处理 (计划中)
- ⏳ 工作流管理 (计划中)

## Agent类型

当前支持的Agent类型：
- **research**: 研究Agent - 用于信息研究和分析
- **coding**: 编程Agent - 用于代码生成和编程任务
- **writing**: 写作Agent - 用于文本创作和写作

## 开发命令

```bash
# 运行测试
uv run pytest

# 代码格式化
uv run black app/

# 类型检查
uv run mypy app/

# 创建新的数据库迁移
uv run alembic revision --autogenerate -m "描述"
```
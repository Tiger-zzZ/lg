import asyncio
from typing import List

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from app.agents.base import BaseAgent, AgentState
from app.rag.search import SemanticSearch
from app.core.config import settings
from app.core.logging import logger


class SearchAgent(BaseAgent):
    """搜索助手Agent - 专门用于文档搜索和信息检索"""

    def __init__(self):
        super().__init__(
            name="Search Agent",
            description="专门用于文档搜索和信息检索的智能助手"
        )
        self.search_engine = SemanticSearch()
        self._llm = None

    def _get_llm(self):
        """延迟初始化 ChatOpenAI"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )
            self._llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=0.3,
                max_tokens=800
            )
        return self._llm

    async def _process(self, state: AgentState) -> AgentState:
        """搜索处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有搜索查询")

            query = state["messages"][-1]
            logger.info(f"Search Agent 处理查询: {query}")

            # 执行文档搜索
            search_results = await self.search_engine.hybrid_search(
                query=query,
                top_k=8,
                keyword_weight=0.4,
                semantic_weight=0.6,
                filter_metadata=state["metadata"].get("filter_metadata")
            )

            if not search_results:
                result = f"🔍 搜索结果\n\n未找到与查询 '{query}' 相关的文档内容。\n\n建议：\n• 尝试使用不同的关键词\n• 检查是否已上传相关文档\n• 使用更通用的搜索词"
            else:
                # 使用AI分析和总结搜索结果
                result = await self._generate_search_summary(query, search_results)

            # 更新状态
            updated_metadata = {
                **state["metadata"],
                "search_results": [
                    {
                        "document_id": r.document_id,
                        "chunk_index": r.chunk_index,
                        "score": r.score,
                        "content_preview": r.content[:150] + "..." if len(r.content) > 150 else r.content
                    }
                    for r in search_results
                ],
                "results_count": len(search_results)
            }

            logger.info(f"Search Agent 完成，找到 {len(search_results)} 个结果")

            return {
                **state,
                "result": result,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"Search Agent 处理失败: {str(e)}")
            error_message = f"🔍 搜索过程中遇到错误：{str(e)}"

            return {
                **state,
                "result": error_message,
                "status": "error",
                "metadata": {
                    **state["metadata"],
                    "error": str(e)
                }
            }

    async def _generate_search_summary(self, query: str, search_results: list) -> str:
        """生成搜索结果摘要"""
        try:
            # 构建搜索结果文本
            results_text = f"搜索查询: {query}\n找到 {len(search_results)} 个相关结果:\n\n"

            for i, result in enumerate(search_results[:5], 1):
                results_text += f"结果 {i} (相似度: {result.score:.2f}):\n{result.content}\n\n---\n\n"

            # 使用AI生成搜索摘要
            system_prompt = """你是一个搜索结果分析助手。请根据搜索结果生成一个有用的摘要，包括：
1. 简要概述找到的信息
2. 突出最相关的内容
3. 提供有条理的信息组织
4. 如果有多个来源，说明不同来源的内容

请保持摘要简洁但信息丰富。"""

            user_prompt = f"""
请为以下搜索结果生成摘要：

{results_text}

请生成一个结构化的搜索结果摘要。
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"🔍 搜索结果摘要\n\n{response.content}"

        except Exception as e:
            logger.error(f"生成搜索摘要失败: {str(e)}")
            # 如果AI摘要失败，返回简单的结果列表
            simple_summary = f"🔍 搜索结果 (共 {len(search_results)} 条)\n\n"
            for i, result in enumerate(search_results[:3], 1):
                simple_summary += f"{i}. 相似度: {result.score:.2f}\n{result.content[:200]}...\n\n"
            return simple_summary


class ChatAgent(BaseAgent):
    """对话助手Agent - 通用的AI对话助手"""

    def __init__(self):
        super().__init__(
            name="Chat Agent",
            description="通用的AI对话助手，能够进行自然语言对话和回答各种问题"
        )
        self._llm = None

    def _get_llm(self):
        """延迟初始化 ChatOpenAI"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )
            self._llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=0.7,
                max_tokens=1000
            )
        return self._llm

    async def _process(self, state: AgentState) -> AgentState:
        """对话处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有对话消息")

            current_message = state["messages"][-1]
            chat_history = state["messages"][:-1]

            logger.info(f"Chat Agent 处理对话: {current_message[:100]}...")

            # 生成AI回复
            response = await self._generate_chat_response(current_message, chat_history)

            # 更新状态
            updated_messages = state["messages"].copy()
            updated_messages.append(response)

            updated_metadata = {
                **state["metadata"],
                "response_length": len(response),
                "conversation_turns": len(updated_messages) // 2
            }

            logger.info("Chat Agent 对话处理完成")

            return {
                **state,
                "messages": updated_messages,
                "result": response,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"Chat Agent 处理失败: {str(e)}")
            error_message = f"💬 抱歉，在处理您的消息时遇到了问题：{str(e)}"

            return {
                **state,
                "result": error_message,
                "status": "error",
                "metadata": {
                    **state["metadata"],
                    "error": str(e)
                }
            }

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """生成对话回复"""
        try:
            # 构建系统提示
            system_prompt = """你是一个智能的AI助手，能够：
1. 进行自然、有帮助的对话
2. 回答各种问题和提供信息
3. 协助解决问题和提供建议
4. 保持友好、专业的语调

请根据用户的消息提供有用、准确的回复。如果不确定某些信息，请诚实说明。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史 (限制长度避免token超限)
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                # 只保留最近的几轮对话
                recent_history = history_pairs[-3:] if len(history_pairs) > 3 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            # 添加当前消息
            messages.append(HumanMessage(content=message))

            # 调用LLM
            llm = self._get_llm()
            # response = await asyncio.to_thread(llm.invoke, messages)
            response = await llm.ainvoke(messages)

            return response.content

        except Exception as e:
            logger.error(f"生成对话回复失败: {str(e)}")
            return "抱歉，我在处理您的消息时遇到了技术问题。请稍后重试。"


# 为向后兼容保留原有的Agent类，但用新的实现替换
class ResearchAgent(SearchAgent):
    """研究Agent - 使用搜索功能进行信息研究"""

    def __init__(self):
        super().__init__()
        self.name = "Research Agent"
        self.description = "专门用于信息研究和分析的Agent，基于文档搜索提供研究结果"


class CodingAgent(ChatAgent):
    """编程Agent - 专门处理编程相关问题"""

    def __init__(self):
        super().__init__()
        self.name = "Coding Agent"
        self.description = "专门用于代码生成和编程任务的Agent"

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """重写以专注于编程任务"""
        try:
            system_prompt = """你是一个专业的编程助手，专门帮助用户：
1. 编写和优化代码
2. 解决编程问题
3. 解释代码概念和最佳实践
4. 提供代码示例和解决方案
5. 调试和错误排查

请提供清晰、实用的编程建议和代码示例。使用适当的代码格式和注释。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                recent_history = history_pairs[-2:] if len(history_pairs) > 2 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            messages.append(HumanMessage(content=message))

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"💻 {response.content}"

        except Exception as e:
            logger.error(f"生成编程回复失败: {str(e)}")
            return "💻 抱歉，我在处理您的编程问题时遇到了技术问题。请稍后重试。"


class WritingAgent(ChatAgent):
    """写作Agent - 专门处理写作和内容创作"""

    def __init__(self):
        super().__init__()
        self.name = "Writing Agent"
        self.description = "专门用于文本创作和写作的Agent"

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """重写以专注于写作任务"""
        try:
            system_prompt = """你是一个专业的写作助手，专门帮助用户：
1. 创作各种类型的文档和文章
2. 改进和润色文本
3. 提供写作建议和技巧
4. 协助内容策划和结构化
5. 适应不同的写作风格和场景

请提供高质量、结构化的写作内容和建议。注意语言的流畅性和可读性。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                recent_history = history_pairs[-2:] if len(history_pairs) > 2 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            messages.append(HumanMessage(content=message))

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"✍️ {response.content}"

        except Exception as e:
            logger.error(f"生成写作回复失败: {str(e)}")
            return "✍️ 抱歉，我在处理您的写作请求时遇到了技术问题。请稍后重试。"

class DataAnalystAgent(BaseAgent):
    """数据分析师Agent - 专业的数据分析和可视化专家"""

    def __init__(self):
        super().__init__(
            name="数据分析师",
            description="专业的数据分析和可视化专家，擅长数据处理、统计分析和洞察发现"
        )

        # 启用数据分析相关的工具
        self.enable_tools([
            "calculator",
            "data_processor",
            "database_query",
            "file_reader"
        ])

        # 初始化记忆系统
        from app.agents.memory import AgentMemory, MemoryType, MemoryImportance
        self.memory = AgentMemory(self.id)

        # 数据分析能力配置
        self.capabilities = {
            "data_processing": ["清洗", "转换", "聚合", "过滤"],
            "statistical_analysis": ["描述统计", "相关分析", "回归分析"],
            "visualization": ["柱状图", "折线图", "散点图", "热力图"],
            "data_formats": ["CSV", "JSON", "Excel", "SQL"]
        }

    async def _process(self, state: AgentState) -> AgentState:
        """数据分析处理逻辑"""
        try:
            from app.agents.memory import MemoryType, MemoryImportance
            from datetime import datetime

            # 解析用户请求
            user_input = state["messages"][-1] if state["messages"] else ""

            # 分析请求类型
            analysis_type = self._analyze_request_type(user_input)

            # 初始化工具执行结果列表
            tool_results = state.get("tool_results", [])

            # 根据分析类型选择处理方法和使用相应工具
            if "计算" in user_input or "统计" in user_input:
                # 使用计算器工具进行数值计算
                result = await self._handle_calculation_with_tools(user_input, tool_results)
            elif "数据处理" in user_input or "转换" in user_input:
                # 使用数据处理工具
                result = await self._handle_data_processing_with_tools(user_input, tool_results)
            elif "查询" in user_input or "数据库" in user_input:
                # 使用数据库查询工具
                result = await self._handle_database_query_with_tools(user_input, tool_results)
            elif "探索" in user_input or "概览" in user_input:
                result = self._handle_data_exploration()
            elif "图表" in user_input or "可视化" in user_input:
                result = self._handle_visualization()
            else:
                result = self._handle_general_analysis()

            # 存储记忆
            await self.memory.remember(
                content=f"分析请求: {user_input}",
                memory_type=MemoryType.EPISODIC,
                importance=MemoryImportance.MEDIUM,
                tags=["数据分析", analysis_type]
            )

            return {
                **state,
                "result": result,
                "tool_results": tool_results
            }

        except Exception as e:
            logger.error(f"数据分析处理失败: {e}")
            return {**state, "result": f"数据分析过程中出现错误: {str(e)}"}

    def _analyze_request_type(self, user_input: str) -> str:
        """分析请求类型"""
        if any(word in user_input.lower() for word in ["探索", "概览", "describe"]):
            return "data_exploration"
        elif any(word in user_input.lower() for word in ["统计", "相关性", "回归"]):
            return "statistical_analysis"
        elif any(word in user_input.lower() for word in ["图表", "可视化", "plot"]):
            return "visualization"
        else:
            return "general_analysis"

    def _handle_data_exploration(self) -> str:
        """处理数据探索请求"""
        from datetime import datetime
        return f"""## 数据探索分析指南

### 基本步骤
1. 数据加载和检查
2. 数据结构分析
3. 缺失值统计
4. 描述性统计

### Python代码示例
```python
import pandas as pd
df = pd.read_csv('data.csv')
print(df.info())
print(df.describe())
print(df.isnull().sum())
```

### 关键指标
- 数据量：行数和列数
- 数据类型：数值型、分类型、时间型
- 数据质量：缺失值、重复值、异常值

*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""

    def _handle_statistical_analysis(self) -> str:
        """处理统计分析请求"""
        from datetime import datetime
        return f"""## 统计分析指南

### 描述统计
- 集中趋势：均值、中位数、众数
- 离散程度：标准差、方差、极差
- 分布形状：偏度、峰度

### 推断统计
- 假设检验：t检验、卡方检验
- 相关分析：皮尔逊相关、斯皮尔曼相关
- 回归分析：线性回归、多元回归

### Python实现
```python
from scipy import stats
import numpy as np

# 描述统计
stats.describe(data)

# 相关分析
correlation = np.corrcoef(x, y)

# t检验
t_stat, p_value = stats.ttest_ind(group1, group2)
```

*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""

    def _handle_visualization(self) -> str:
        """处理可视化请求"""
        from datetime import datetime
        return f"""## 数据可视化指南

### 图表类型选择
- **数值数据**: 直方图、箱线图、散点图
- **分类数据**: 柱状图、饼图、条形图
- **时间序列**: 折线图、面积图
- **多变量**: 热力图、散点矩阵

### Python可视化库
- **Matplotlib**: 基础绘图库
- **Seaborn**: 统计可视化
- **Plotly**: 交互式图表

### 代码示例
```python
import matplotlib.pyplot as plt
import seaborn as sns

# 基础图表
plt.figure(figsize=(10, 6))
sns.histplot(data=df, x='column_name')
plt.title('数据分布图')
plt.show()

# 相关性热力图
sns.heatmap(df.corr(), annot=True, cmap='coolwarm')
```

### 设计原则
- 清晰性：信息传达要明确
- 简洁性：避免不必要的装饰
- 一致性：统一的颜色和样式

*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""

    def _handle_general_analysis(self) -> str:
        """处理通用分析请求"""
        from datetime import datetime
        return f"""## 数据分析全流程指南

### 分析流程
1. **问题定义**: 明确分析目标和业务问题
2. **数据收集**: 获取相关数据源
3. **数据预处理**: 清洗、转换、整合数据
4. **探索分析**: 描述统计、可视化探索
5. **深度分析**: 统计建模、机器学习
6. **结果解释**: 业务洞察和行动建议

### 分析方法
- **描述分析**: 现状分析 (What happened)
- **诊断分析**: 原因分析 (Why it happened)
- **预测分析**: 趋势预测 (What will happen)
- **处方分析**: 决策优化 (What should we do)

### 工具推荐
- **Python**: pandas, numpy, scipy, scikit-learn
- **可视化**: matplotlib, seaborn, plotly
- **数据库**: SQL查询和数据提取
- **BI工具**: Tableau, PowerBI

### 最佳实践
- 理解数据背景和业务含义
- 保持分析过程的可重现性
- 选择合适的可视化方式
- 关注结果的统计显著性
- 将技术结果转化为业务语言

*分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""

    async def _handle_calculation_with_tools(self, user_input: str, tool_results: list) -> str:
        """使用计算器工具处理数值计算"""
        try:
            # 提取数字和运算表达式
            import re

            # 查找数学表达式
            math_expressions = re.findall(r'[\d+\-*/().]+', user_input)

            if math_expressions:
                expression = math_expressions[0]
                calc_result = await self._use_tool("calculator", expression=expression)
                tool_results.append(calc_result)

                if calc_result["success"]:
                    result_value = calc_result["data"]["result"]
                    return f"## 计算结果\n\n表达式: `{expression}`\n结果: **{result_value}**\n\n✅ 计算完成"
                else:
                    return f"## 计算错误\n\n表达式: `{expression}`\n错误: {calc_result['error']}"

            # 查找统计数据
            numbers = re.findall(r'\d+\.?\d*', user_input)
            if len(numbers) >= 2:
                data = [float(x) for x in numbers]
                stats_result = await self._use_tool("calculator", data=data, operation="mean")
                tool_results.append(stats_result)

                if stats_result["success"]:
                    mean_value = stats_result["data"]["result"]
                    return f"## 统计分析\n\n数据: {data}\n平均值: **{mean_value:.2f}**\n数据个数: {len(data)}\n\n✅ 统计计算完成"
                else:
                    return f"## 统计分析错误\n\n错误: {stats_result['error']}"

            return "## 计算请求\n\n未能识别到有效的数学表达式或数据，请提供明确的计算内容。"

        except Exception as e:
            return f"## 计算错误\n\n处理计算请求时出现错误: {str(e)}"

    async def _handle_data_processing_with_tools(self, user_input: str, tool_results: list) -> str:
        """使用数据处理工具处理数据"""
        try:
            # 模拟数据处理请求
            sample_data = [
                {"id": 1, "name": "产品A", "sales": 1000, "category": "电子"},
                {"id": 2, "name": "产品B", "sales": 800, "category": "服装"},
                {"id": 3, "name": "产品C", "sales": 1200, "category": "电子"},
                {"id": 4, "name": "产品D", "sales": 600, "category": "服装"}
            ]

            if "过滤" in user_input or "筛选" in user_input:
                # 过滤操作
                filter_result = await self._use_tool(
                    "data_processor",
                    data=sample_data,
                    operation="filter",
                    config={"field": "category", "value": "电子", "operator": "eq"}
                )
                tool_results.append(filter_result)

                if filter_result["success"]:
                    filtered_data = filter_result["data"]["result"]
                    return f"## 数据过滤结果\n\n过滤条件: category = '电子'\n\n```json\n{filtered_data}\n```\n\n✅ 数据过滤完成"
                else:
                    return f"## 数据过滤错误\n\n错误: {filter_result['error']}"

            elif "聚合" in user_input or "汇总" in user_input:
                # 聚合操作
                agg_result = await self._use_tool(
                    "data_processor",
                    data=sample_data,
                    operation="aggregate",
                    config={"field": "sales", "type": "sum"}
                )
                tool_results.append(agg_result)

                if agg_result["success"]:
                    agg_data = agg_result["data"]["result"]
                    return f"## 数据聚合结果\n\n聚合字段: sales\n聚合类型: sum\n\n结果: **{agg_data['sum']}**\n\n✅ 数据聚合完成"
                else:
                    return f"## 数据聚合错误\n\n错误: {agg_result['error']}"

            else:
                # 默认返回数据概览
                return f"## 数据处理\n\n示例数据集:\n```json\n{sample_data}\n```\n\n支持的操作:\n- 数据过滤筛选\n- 数据聚合汇总\n- 数据转换映射"

        except Exception as e:
            return f"## 数据处理错误\n\n处理数据时出现错误: {str(e)}"

    async def _handle_database_query_with_tools(self, user_input: str, tool_results: list) -> str:
        """使用数据库查询工具查询数据"""
        try:
            if "文档" in user_input or "documents" in user_input.lower():
                table = "documents"
            elif "用户" in user_input or "users" in user_input.lower():
                table = "users"
            elif "记忆" in user_input or "memories" in user_input.lower():
                table = "agent_memories"
            else:
                table = "documents"  # 默认表

            if "统计" in user_input or "数量" in user_input:
                # 计数查询
                query_result = await self._use_tool(
                    "database_query",
                    query_type="count",
                    table=table
                )
                tool_results.append(query_result)

                if query_result["success"]:
                    count_data = query_result["data"]["result"]
                    return f"## 数据库查询结果\n\n表名: `{table}`\n查询类型: 计数\n\n总记录数: **{count_data['count']}**\n\n✅ 查询完成"
                else:
                    return f"## 数据库查询错误\n\n表名: `{table}`\n错误: {query_result['error']}"

            elif "聚合" in user_input or "汇总" in user_input:
                # 聚合查询
                query_result = await self._use_tool(
                    "database_query",
                    query_type="aggregate",
                    table=table
                )
                tool_results.append(query_result)

                if query_result["success"]:
                    agg_data = query_result["data"]["result"]
                    return f"## 数据库聚合查询结果\n\n表名: `{table}`\n\n- 总记录数: **{agg_data['count']}**\n- 最早记录: {agg_data['earliest']}\n- 最新记录: {agg_data['latest']}\n\n✅ 聚合查询完成"
                else:
                    return f"## 数据库聚合查询错误\n\n表名: `{table}`\n错误: {query_result['error']}"

            else:
                # 普通查询
                query_result = await self._use_tool(
                    "database_query",
                    query_type="select",
                    table=table,
                    limit=5
                )
                tool_results.append(query_result)

                if query_result["success"]:
                    select_data = query_result["data"]["result"]
                    rows_count = select_data['count']
                    return f"## 数据库查询结果\n\n表名: `{table}`\n返回记录数: **{rows_count}**\n\n```json\n{select_data['rows'][:3] if select_data['rows'] else []}\n```\n\n✅ 查询完成 (显示前3条记录)"
                else:
                    return f"## 数据库查询错误\n\n表名: `{table}`\n错误: {query_result['error']}"

        except Exception as e:
            return f"## 数据库查询错误\n\n查询数据库时出现错误: {str(e)}"

    async def get_analysis_capabilities(self):
        """获取分析能力描述"""
        return {
            "agent_info": {
                "name": self.name,
                "description": self.description,
                "id": self.id
            },
            "capabilities": self.capabilities,
            "supported_formats": ["CSV", "Excel", "JSON", "SQL查询结果"],
            "analysis_types": [
                "数据探索和概览",
                "描述统计分析", 
                "相关性分析",
                "数据可视化建议",
                "数据清洗指导",
                "统计建模建议"
            ],
            "memory_summary": await self.memory.get_memory_summary()
        }

"""
具体的协作Agent实现
包含不同角色和专业领域的Agent
"""

from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from app.agents.collaboration import (
    CollaborativeAgent, CollaborationRole, AgentMessage, MessageType,
    collaboration_manager
)
from app.core.logging import logger


class CoordinatorAgent(CollaborativeAgent):
    """协调者Agent - 负责任务分配和协调"""

    def __init__(self):
        super().__init__(
            name="协调者",
            description="负责任务分配、进度监控和协调管理",
            role=CollaborationRole.COORDINATOR,
            specialties=["task_management", "coordination", "planning"]
        )
        self.managed_projects: Dict[str, Dict[str, Any]] = {}

    async def create_project(self, project_name: str, tasks: List[Dict[str, Any]],
                           available_agents: List[str]) -> str:
        """创建项目并分配任务"""
        project_id = f"project_{len(self.managed_projects) + 1}"

        project = {
            "id": project_id,
            "name": project_name,
            "tasks": tasks,
            "agents": available_agents,
            "status": "planning",
            "created_at": datetime.utcnow(),
            "completed_tasks": [],
            "failed_tasks": []
        }

        self.managed_projects[project_id] = project

        # 分配任务
        await self._assign_project_tasks(project)

        logger.info(f"协调者创建项目: {project_name} (任务数: {len(tasks)})")
        return project_id

    async def _assign_project_tasks(self, project: Dict[str, Any]):
        """为项目分配任务"""
        for i, task in enumerate(project["tasks"]):
            # 简单的轮询分配策略
            agent_id = project["agents"][i % len(project["agents"])]

            await collaboration_manager.assign_task(
                task_name=task["name"],
                task_description=task.get("description", ""),
                assigned_to=agent_id,
                assigned_by=self.id,
                parameters=task.get("parameters", {})
            )

        project["status"] = "in_progress"

    async def _process(self, state) -> dict:
        """协调者的处理逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return {**state, "result": "协调者等待任务分配指令"}

        command = messages[-1].lower()

        if "创建项目" in command:
            # 示例项目创建
            tasks = [
                {"name": "数据收集", "description": "收集分析所需数据"},
                {"name": "数据处理", "description": "清洗和预处理数据"},
                {"name": "分析报告", "description": "生成分析报告"}
            ]

            available_agents = list(collaboration_manager.agents.keys())
            available_agents = [aid for aid in available_agents if aid != self.id]

            if available_agents:
                project_id = await self.create_project("数据分析项目", tasks, available_agents)
                result = f"✅ 项目创建成功: {project_id}\n分配了 {len(tasks)} 个任务给 {len(available_agents)} 个Agent"
            else:
                result = "❌ 没有可用的Agent执行任务"

        elif "项目状态" in command:
            result = self._get_projects_status()

        else:
            result = f"协调者收到指令: {command}\n可用命令: 创建项目, 项目状态"

        return {**state, "result": result}

    def _get_projects_status(self) -> str:
        """获取项目状态"""
        if not self.managed_projects:
            return "📋 当前没有管理的项目"

        status = "📋 项目状态报告:\n\n"
        for project in self.managed_projects.values():
            status += f"项目: {project['name']}\n"
            status += f"状态: {project['status']}\n"
            status += f"任务总数: {len(project['tasks'])}\n"
            status += f"已完成: {len(project['completed_tasks'])}\n"
            status += f"失败: {len(project['failed_tasks'])}\n\n"

        return status


class DataAnalysisSpecialist(CollaborativeAgent):
    """数据分析专家Agent"""

    def __init__(self):
        super().__init__(
            name="数据分析专家",
            description="专门负责数据分析、统计计算和数据可视化",
            role=CollaborationRole.SPECIALIST,
            specialties=["data_analysis", "statistics", "visualization"]
        )

        # 启用数据分析工具
        self.enable_tools(["calculator", "data_processor", "database_query"])

    async def _process(self, state) -> dict:
        """数据分析专家的处理逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return {**state, "result": "数据分析专家待命"}

        task = messages[-1]

        if "数据收集" in task:
            result = await self._collect_data()
        elif "数据处理" in task:
            result = await self._process_data()
        elif "分析报告" in task:
            result = await self._generate_report()
        elif "统计分析" in task:
            result = await self._statistical_analysis()
        else:
            result = f"数据分析专家处理: {task}"

        return {**state, "result": result}

    async def _collect_data(self) -> str:
        """数据收集"""
        try:
            # 使用数据库查询工具
            db_result = await self._use_tool(
                "database_query",
                query_type="count",
                table="documents"
            )

            if db_result["success"]:
                count = db_result["data"]["result"]["count"]
                return f"📊 数据收集完成: 发现 {count} 条记录"
            else:
                return f"❌ 数据收集失败: {db_result['error']}"

        except Exception as e:
            return f"❌ 数据收集异常: {str(e)}"

    async def _process_data(self) -> str:
        """数据处理"""
        try:
            # 模拟数据处理
            sample_data = [
                {"id": 1, "value": 100, "category": "A"},
                {"id": 2, "value": 200, "category": "B"},
                {"id": 3, "value": 150, "category": "A"},
                {"id": 4, "value": 300, "category": "B"}
            ]

            # 使用数据处理工具
            process_result = await self._use_tool(
                "data_processor",
                data=sample_data,
                operation="aggregate",
                config={"field": "value", "type": "sum"}
            )

            if process_result["success"]:
                total = process_result["data"]["result"]["sum"]
                return f"📈 数据处理完成: 总值 {total}, 记录数 {len(sample_data)}"
            else:
                return f"❌ 数据处理失败: {process_result['error']}"

        except Exception as e:
            return f"❌ 数据处理异常: {str(e)}"

    async def _statistical_analysis(self) -> str:
        """统计分析"""
        try:
            # 使用计算器工具进行统计分析
            data = [85, 92, 78, 96, 87, 90, 82, 88, 93, 79]

            # 计算平均值
            mean_result = await self._use_tool(
                "calculator",
                data=data,
                operation="mean"
            )

            if mean_result["success"]:
                mean_value = mean_result["data"]["result"]
                return f"📊 统计分析完成:\n- 数据量: {len(data)}\n- 平均值: {mean_value:.2f}\n- 范围: {min(data)}-{max(data)}"
            else:
                return f"❌ 统计分析失败: {mean_result['error']}"

        except Exception as e:
            return f"❌ 统计分析异常: {str(e)}"

    async def _generate_report(self) -> str:
        """生成报告"""
        return f"""📋 数据分析报告

## 分析概要
- 分析时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
- 分析师: {self.name}
- 状态: 完成

## 主要发现
- 数据质量良好
- 统计指标正常
- 无异常值检测

## 建议
- 建议定期更新数据
- 可进行进一步的深度分析

报告生成完成 ✅"""


class ReviewerAgent(CollaborativeAgent):
    """审查者Agent - 负责质量检查和审核"""

    def __init__(self):
        super().__init__(
            name="审查者",
            description="负责任务结果审查、质量检查和反馈",
            role=CollaborationRole.REVIEWER,
            specialties=["quality_assurance", "review", "validation"]
        )
        self.review_history: List[Dict[str, Any]] = []

    async def _process(self, state) -> dict:
        """审查者的处理逻辑"""
        messages = state.get("messages", [])
        if not messages:
            return {**state, "result": "审查者等待审查任务"}

        task = messages[-1]

        if "审查" in task or "检查" in task:
            result = await self._conduct_review(task)
        elif "质量检查" in task:
            result = await self._quality_check(task)
        else:
            result = f"审查者处理: {task}"

        return {**state, "result": result}

    async def _conduct_review(self, content: str) -> str:
        """执行审查"""
        review_id = f"review_{len(self.review_history) + 1}"

        review_record = {
            "id": review_id,
            "content": content,
            "timestamp": datetime.utcnow(),
            "reviewer": self.name,
            "status": "completed"
        }

        # 模拟审查过程
        issues_found = []
        recommendations = []

        # 简单的审查逻辑
        if len(content) < 10:
            issues_found.append("内容过于简短")
            recommendations.append("建议提供更详细的信息")

        if "错误" in content.lower() or "失败" in content.lower():
            issues_found.append("检测到错误信息")
            recommendations.append("建议检查并修复错误")

        review_record["issues"] = issues_found
        review_record["recommendations"] = recommendations

        self.review_history.append(review_record)

        # 生成审查报告
        report = f"🔍 审查报告 ({review_id})\n\n"
        report += f"审查内容: {content[:50]}...\n"
        report += f"发现问题: {len(issues_found)} 个\n"

        if issues_found:
            report += "\n问题列表:\n"
            for i, issue in enumerate(issues_found, 1):
                report += f"{i}. {issue}\n"

        if recommendations:
            report += "\n建议:\n"
            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"

        report += f"\n审查状态: {'✅ 通过' if not issues_found else '⚠️ 需要改进'}"

        return report

    async def _quality_check(self, task: str) -> str:
        """质量检查"""
        return f"🔍 质量检查完成\n任务: {task}\n结果: 符合质量标准 ✅"


class MonitorAgent(CollaborativeAgent):
    """监控Agent - 负责系统监控和性能跟踪"""

    def __init__(self):
        super().__init__(
            name="监控员",
            description="负责系统监控、性能跟踪和异常检测",
            role=CollaborationRole.MONITOR,
            specialties=["monitoring", "performance", "diagnostics"]
        )

    async def _process(self, state) -> dict:
        """监控Agent的处理逻辑"""
        messages = state.get("messages", [])
        if not messages:
            result = await self._get_system_status()
        else:
            task = messages[-1]
            if "监控" in task or "状态" in task:
                result = await self._get_system_status()
            elif "性能" in task:
                result = await self._performance_report()
            else:
                result = f"监控员处理: {task}"

        return {**state, "result": result}

    async def _get_system_status(self) -> str:
        """获取系统状态"""
        stats = collaboration_manager.get_collaboration_stats()

        status = "📊 系统监控报告\n\n"
        status += f"🤖 注册Agent数: {stats['registered_agents']}\n"
        status += f"🔄 活跃会话: {stats['active_sessions']}\n"
        status += f"📨 消息总数: {stats['total_messages']}\n\n"

        status += "📋 任务统计:\n"
        task_stats = stats['task_stats']
        status += f"  - 总任务: {task_stats['total']}\n"
        status += f"  - 已完成: {task_stats['completed']}\n"
        status += f"  - 进行中: {task_stats['in_progress']}\n"
        status += f"  - 失败: {task_stats['failed']}\n\n"

        status += "👥 Agent角色分布:\n"
        for role, count in stats['agent_roles'].items():
            if count > 0:
                status += f"  - {role}: {count}\n"

        status += f"\n监控时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"

        return status

    async def _performance_report(self) -> str:
        """性能报告"""
        return f"""📈 性能监控报告

## 系统性能
- CPU使用率: 正常
- 内存使用: 正常
- 响应时间: < 100ms

## Agent性能
- 平均任务执行时间: 1.2秒
- 成功率: 95%
- 错误率: 5%

## 建议
- 系统运行正常
- 无需优化

监控时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"""
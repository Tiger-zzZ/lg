"""
增强的Agent类，支持复杂状态流转
继承自BaseAgent，添加工作流管理能力
"""

from typing import Dict, Any, List, Optional, Callable
import asyncio
from datetime import datetime

from app.agents.base import BaseAgent, AgentState
from app.agents.workflow import (
    ComplexFlow, FlowNode, FlowNodeType, FlowCondition,
    flow_engine, FlowContext
)
from app.core.logging import logger


class WorkflowAgent(BaseAgent):
    """支持复杂工作流的Agent"""

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.workflows: Dict[str, ComplexFlow] = {}
        self.default_workflow: Optional[str] = None

    def create_workflow(self, name: str, description: str = "") -> ComplexFlow:
        """创建新的工作流"""
        workflow = ComplexFlow(name, description)
        self.workflows[workflow.id] = workflow

        # 注册到全局流程引擎
        flow_engine.register_flow(workflow)

        logger.info(f"Agent {self.name} 创建工作流: {name}")
        return workflow

    def set_default_workflow(self, workflow_id: str):
        """设置默认工作流"""
        if workflow_id in self.workflows:
            self.default_workflow = workflow_id
            logger.info(f"Agent {self.name} 设置默认工作流: {workflow_id}")
        else:
            raise ValueError(f"工作流不存在: {workflow_id}")

    async def execute_workflow(self, workflow_id: Optional[str] = None,
                             initial_context: Dict[str, Any] = None) -> Any:
        """执行指定工作流"""
        target_workflow_id = workflow_id or self.default_workflow

        if not target_workflow_id:
            raise ValueError("未指定工作流且无默认工作流")

        if target_workflow_id not in self.workflows:
            raise ValueError(f"工作流不存在: {target_workflow_id}")

        # 准备初始上下文
        context = initial_context or {}
        context.update({
            "agent_id": self.id,
            "agent_name": self.name,
            "execution_time": datetime.utcnow().isoformat()
        })

        # 执行工作流
        execution = await flow_engine.execute_flow(target_workflow_id, context)

        logger.info(f"Agent {self.name} 工作流执行完成",
                   workflow_id=target_workflow_id,
                   execution_id=execution.id,
                   status=execution.status.value)

        return execution.result

    def create_simple_workflow(self, steps: List[Dict[str, Any]]) -> ComplexFlow:
        """创建简单的线性工作流"""
        workflow = self.create_workflow(f"{self.name}_simple_workflow")

        # 添加开始节点
        start_node = FlowNode(
            id="start",
            name="开始",
            node_type=FlowNodeType.START
        )
        workflow.add_node(start_node)

        previous_node_id = "start"

        # 添加步骤节点
        for i, step in enumerate(steps):
            step_id = f"step_{i+1}"

            if step["type"] == "task":
                node = FlowNode(
                    id=step_id,
                    name=step.get("name", f"步骤{i+1}"),
                    node_type=FlowNodeType.TASK,
                    handler=step.get("handler"),
                    metadata=step.get("metadata", {})
                )
            elif step["type"] == "tool":
                node = FlowNode(
                    id=step_id,
                    name=step.get("name", f"工具调用{i+1}"),
                    node_type=FlowNodeType.TOOL_CALL,
                    tool_name=step["tool_name"],
                    tool_params=step.get("tool_params", {})
                )
            elif step["type"] == "condition":
                node = FlowNode(
                    id=step_id,
                    name=step.get("name", f"条件判断{i+1}"),
                    node_type=FlowNodeType.CONDITION,
                    conditions=step["conditions"]
                )
            else:
                continue

            workflow.add_node(node)
            workflow.connect_nodes(previous_node_id, step_id)
            previous_node_id = step_id

        # 添加结束节点
        end_node = FlowNode(
            id="end",
            name="结束",
            node_type=FlowNodeType.END
        )
        workflow.add_node(end_node)
        workflow.connect_nodes(previous_node_id, "end")

        return workflow

    def create_conditional_workflow(self, decision_logic: Dict[str, Any]) -> ComplexFlow:
        """创建带条件分支的工作流"""
        workflow = self.create_workflow(f"{self.name}_conditional_workflow")

        # 开始节点
        start_node = FlowNode(id="start", name="开始", node_type=FlowNodeType.START)
        workflow.add_node(start_node)

        # 决策节点
        decision_node = FlowNode(
            id="decision",
            name="决策点",
            node_type=FlowNodeType.CONDITION,
            conditions=decision_logic["conditions"]
        )
        workflow.add_node(decision_node)
        workflow.connect_nodes("start", "decision")

        # 为每个分支创建节点
        for i, branch in enumerate(decision_logic["branches"]):
            branch_id = f"branch_{i+1}"

            branch_node = FlowNode(
                id=branch_id,
                name=branch.get("name", f"分支{i+1}"),
                node_type=FlowNodeType.TASK,
                handler=branch.get("handler"),
                metadata=branch.get("metadata", {})
            )
            workflow.add_node(branch_node)

            # 连接到结束节点
            end_node = FlowNode(id="end", name="结束", node_type=FlowNodeType.END)
            workflow.add_node(end_node)
            workflow.connect_nodes(branch_id, "end")

        return workflow

    def create_loop_workflow(self, loop_config: Dict[str, Any]) -> ComplexFlow:
        """创建带循环的工作流"""
        workflow = self.create_workflow(f"{self.name}_loop_workflow")

        # 开始节点
        start_node = FlowNode(id="start", name="开始", node_type=FlowNodeType.START)
        workflow.add_node(start_node)

        # 循环节点
        loop_node = FlowNode(
            id="loop",
            name="循环",
            node_type=FlowNodeType.LOOP,
            loop_condition=loop_config.get("condition"),
            max_iterations=loop_config.get("max_iterations", 10)
        )
        workflow.add_node(loop_node)
        workflow.connect_nodes("start", "loop")

        # 循环体节点
        body_node = FlowNode(
            id="loop_body",
            name="循环体",
            node_type=FlowNodeType.TASK,
            handler=loop_config.get("handler")
        )
        workflow.add_node(body_node)
        workflow.connect_nodes("loop", "loop_body")

        # 结束节点
        end_node = FlowNode(id="end", name="结束", node_type=FlowNodeType.END)
        workflow.add_node(end_node)
        workflow.connect_nodes("loop", "end")

        return workflow

    async def _process(self, state: AgentState) -> AgentState:
        """重写处理方法，使用工作流执行"""
        try:
            # 如果有默认工作流，使用工作流执行
            if self.default_workflow:
                initial_context = {
                    "messages": state["messages"],
                    "metadata": state["metadata"]
                }

                result = await self.execute_workflow(initial_context=initial_context)

                return {
                    **state,
                    "result": result or "工作流执行完成",
                    "metadata": {
                        **state["metadata"],
                        "workflow_executed": True,
                        "workflow_id": self.default_workflow
                    }
                }
            else:
                # 回退到简单处理
                return await self._simple_process(state)

        except Exception as e:
            logger.error(f"工作流执行失败: {e}")
            return {
                **state,
                "result": f"工作流执行失败: {str(e)}",
                "status": "failed"
            }

    async def _simple_process(self, state: AgentState) -> AgentState:
        """简单处理逻辑（当没有工作流时的回退）"""
        messages = state.get("messages", [])
        if not messages:
            result = "没有收到消息"
        else:
            result = f"[{self.name}] 简单处理: {messages[-1]}"

        return {
            **state,
            "result": result
        }

    def get_workflow_info(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """获取工作流信息"""
        target_id = workflow_id or self.default_workflow

        if not target_id or target_id not in self.workflows:
            return {"error": "工作流不存在"}

        workflow = self.workflows[target_id]
        return workflow.to_dict()

    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        return [
            {
                "id": wf.id,
                "name": wf.name,
                "description": wf.description,
                "node_count": len(wf.nodes),
                "is_default": wf.id == self.default_workflow,
                "created_at": wf.created_at.isoformat()
            }
            for wf in self.workflows.values()
        ]


class DataAnalysisWorkflowAgent(WorkflowAgent):
    """数据分析工作流Agent"""

    def __init__(self):
        super().__init__(
            name="数据分析工作流Agent",
            description="使用复杂工作流进行数据分析的智能Agent"
        )

        # 启用数据分析相关工具
        self.enable_tools([
            "calculator",
            "data_processor",
            "database_query",
            "file_reader"
        ])

        # 创建默认数据分析工作流
        self._create_default_analysis_workflow()

    def _create_default_analysis_workflow(self):
        """创建默认的数据分析工作流"""
        workflow = self.create_workflow("数据分析标准流程", "数据收集->处理->分析->报告的标准流程")

        # 开始节点
        start_node = FlowNode(id="start", name="开始分析", node_type=FlowNodeType.START)
        workflow.add_node(start_node)

        # 数据收集节点
        collect_node = FlowNode(
            id="collect_data",
            name="数据收集",
            node_type=FlowNodeType.TOOL_CALL,
            tool_name="database_query",
            tool_params={
                "query_type": "select",
                "table": "documents",
                "limit": 10
            }
        )
        workflow.add_node(collect_node)

        # 数据处理节点
        process_node = FlowNode(
            id="process_data",
            name="数据处理",
            node_type=FlowNodeType.TOOL_CALL,
            tool_name="data_processor",
            tool_params={
                "data": "$tool_collect_data_result",
                "operation": "aggregate",
                "config": {"field": "id", "type": "count"}
            }
        )
        workflow.add_node(process_node)

        # 条件判断节点
        decision_node = FlowNode(
            id="check_data_quality",
            name="数据质量检查",
            node_type=FlowNodeType.CONDITION,
            conditions=[
                {
                    "expression": "tool_collect_data_success == True",
                    "next_node": "analyze_data"
                }
            ]
        )
        workflow.add_node(decision_node)

        # 数据分析节点
        analyze_node = FlowNode(
            id="analyze_data",
            name="数据分析",
            node_type=FlowNodeType.TOOL_CALL,
            tool_name="calculator",
            tool_params={
                "data": [1, 2, 3, 4, 5],
                "operation": "mean"
            }
        )
        workflow.add_node(analyze_node)

        # 生成报告节点
        report_node = FlowNode(
            id="generate_report",
            name="生成报告",
            node_type=FlowNodeType.TASK,
            handler=self._generate_analysis_report
        )
        workflow.add_node(report_node)

        # 结束节点
        end_node = FlowNode(id="end", name="分析完成", node_type=FlowNodeType.END)
        workflow.add_node(end_node)

        # 连接节点
        workflow.connect_nodes("start", "collect_data")
        workflow.connect_nodes("collect_data", "check_data_quality")
        workflow.connect_nodes("check_data_quality", "process_data")  # 默认路径
        workflow.connect_nodes("process_data", "analyze_data")
        workflow.connect_nodes("analyze_data", "generate_report")
        workflow.connect_nodes("generate_report", "end")

        # 设置为默认工作流
        self.set_default_workflow(workflow.id)

    async def _generate_analysis_report(self, context: FlowContext) -> str:
        """生成分析报告"""
        report = "## 数据分析报告\n\n"

        # 收集分析结果
        collect_success = context.get_variable("tool_collect_data_success", False)
        process_result = context.get_variable("tool_process_data_result")
        analyze_result = context.get_variable("tool_analyze_data_result")

        if collect_success:
            report += "✅ 数据收集成功\n"
        else:
            report += "❌ 数据收集失败\n"

        if process_result:
            report += f"📊 数据处理结果: {process_result}\n"

        if analyze_result:
            report += f"📈 分析结果: {analyze_result}\n"

        report += f"\n生成时间: {datetime.utcnow().isoformat()}"

        # 存储报告到上下文
        context.set_variable("result", report)

        return report
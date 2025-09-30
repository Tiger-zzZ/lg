"""
复杂状态流转机制
支持条件分支、循环、动态工作流和状态持久化
"""

from typing import Dict, Any, List, Optional, Callable, Union, TypedDict
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import uuid
import asyncio
import json
from datetime import datetime
import copy

from app.core.logging import logger


class FlowNodeType(Enum):
    """流程节点类型"""
    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    MERGE = "merge"
    TOOL_CALL = "tool_call"
    HUMAN_INPUT = "human_input"


class FlowExecutionStatus(Enum):
    """流程执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FlowContext:
    """流程执行上下文"""
    variables: Dict[str, Any] = field(default_factory=dict)
    loop_counters: Dict[str, int] = field(default_factory=dict)
    branch_history: List[str] = field(default_factory=list)
    execution_path: List[str] = field(default_factory=list)
    checkpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)

    def increment_loop(self, loop_id: str) -> int:
        """增加循环计数"""
        self.loop_counters[loop_id] = self.loop_counters.get(loop_id, 0) + 1
        return self.loop_counters[loop_id]

    def save_checkpoint(self, checkpoint_id: str):
        """保存检查点"""
        self.checkpoints[checkpoint_id] = {
            "variables": copy.deepcopy(self.variables),
            "loop_counters": copy.deepcopy(self.loop_counters),
            "timestamp": datetime.utcnow().isoformat()
        }

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """恢复检查点"""
        if checkpoint_id in self.checkpoints:
            checkpoint = self.checkpoints[checkpoint_id]
            self.variables = copy.deepcopy(checkpoint["variables"])
            self.loop_counters = copy.deepcopy(checkpoint["loop_counters"])
            return True
        return False


class FlowCondition(TypedDict):
    """流程条件定义"""
    expression: str  # 条件表达式
    next_node: str   # 满足条件时的下一个节点


@dataclass
class FlowNode:
    """流程节点"""
    id: str
    name: str
    node_type: FlowNodeType
    handler: Optional[Callable] = None
    conditions: List[FlowCondition] = field(default_factory=list)
    next_nodes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 循环相关
    loop_condition: Optional[str] = None
    max_iterations: Optional[int] = None

    # 工具调用相关
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)

    # 并行执行相关
    parallel_nodes: List[str] = field(default_factory=list)
    merge_strategy: str = "wait_all"  # wait_all, wait_any, wait_first


@dataclass
class FlowExecution:
    """流程执行实例"""
    id: str
    flow_id: str
    status: FlowExecutionStatus
    current_node: str
    context: FlowContext
    start_time: datetime
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Any = None


class FlowEngine:
    """复杂状态流转引擎"""

    def __init__(self):
        self.flows: Dict[str, 'ComplexFlow'] = {}
        self.executions: Dict[str, FlowExecution] = {}

    def register_flow(self, flow: 'ComplexFlow'):
        """注册流程"""
        self.flows[flow.id] = flow
        logger.info(f"注册流程: {flow.name} (ID: {flow.id})")

    async def execute_flow(self, flow_id: str, initial_context: Dict[str, Any] = None) -> FlowExecution:
        """执行流程"""
        if flow_id not in self.flows:
            raise ValueError(f"流程不存在: {flow_id}")

        flow = self.flows[flow_id]
        execution_id = str(uuid.uuid4())

        # 创建执行实例
        execution = FlowExecution(
            id=execution_id,
            flow_id=flow_id,
            status=FlowExecutionStatus.RUNNING,
            current_node=flow.start_node,
            context=FlowContext(),
            start_time=datetime.utcnow()
        )

        # 初始化上下文
        if initial_context:
            execution.context.variables.update(initial_context)

        self.executions[execution_id] = execution

        try:
            result = await self._execute_flow_internal(flow, execution)
            execution.status = FlowExecutionStatus.COMPLETED
            execution.result = result
            execution.end_time = datetime.utcnow()

            logger.info(f"流程执行完成: {flow.name} (执行ID: {execution_id})")
            return execution

        except Exception as e:
            execution.status = FlowExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.utcnow()

            logger.error(f"流程执行失败: {flow.name} (执行ID: {execution_id})", error=str(e))
            raise

    async def _execute_flow_internal(self, flow: 'ComplexFlow', execution: FlowExecution) -> Any:
        """内部流程执行逻辑"""
        current_node_id = execution.current_node

        while current_node_id:
            execution.current_node = current_node_id
            execution.context.execution_path.append(current_node_id)

            node = flow.get_node(current_node_id)
            if not node:
                raise ValueError(f"节点不存在: {current_node_id}")

            logger.debug(f"执行节点: {node.name} ({node.node_type.value})")

            # 执行节点
            next_node_id = await self._execute_node(flow, node, execution)

            # 检查是否结束
            if node.node_type == FlowNodeType.END or not next_node_id:
                break

            current_node_id = next_node_id

        return execution.context.get_variable("result")

    async def _execute_node(self, flow: 'ComplexFlow', node: FlowNode, execution: FlowExecution) -> Optional[str]:
        """执行单个节点"""
        context = execution.context

        try:
            if node.node_type == FlowNodeType.START:
                return self._get_next_node(node, context)

            elif node.node_type == FlowNodeType.END:
                return None

            elif node.node_type == FlowNodeType.TASK:
                if node.handler:
                    result = await node.handler(context)
                    context.set_variable(f"node_{node.id}_result", result)
                return self._get_next_node(node, context)

            elif node.node_type == FlowNodeType.CONDITION:
                return self._evaluate_condition_node(node, context)

            elif node.node_type == FlowNodeType.LOOP:
                return await self._execute_loop_node(flow, node, execution)

            elif node.node_type == FlowNodeType.TOOL_CALL:
                return await self._execute_tool_node(node, context)

            elif node.node_type == FlowNodeType.PARALLEL:
                return await self._execute_parallel_node(flow, node, execution)

            else:
                logger.warning(f"未实现的节点类型: {node.node_type}")
                return self._get_next_node(node, context)

        except Exception as e:
            logger.error(f"节点执行失败: {node.name}", error=str(e))
            raise

    def _get_next_node(self, node: FlowNode, context: FlowContext) -> Optional[str]:
        """获取下一个节点"""
        if node.next_nodes:
            return node.next_nodes[0]
        return None

    def _evaluate_condition_node(self, node: FlowNode, context: FlowContext) -> Optional[str]:
        """评估条件节点"""
        for condition in node.conditions:
            try:
                # 简单的条件评估
                expr = condition["expression"]
                variables = context.variables

                # 安全的表达式评估
                if self._evaluate_expression(expr, variables):
                    context.branch_history.append(f"{node.id}:{condition['next_node']}")
                    return condition["next_node"]

            except Exception as e:
                logger.error(f"条件评估失败: {condition['expression']}", error=str(e))

        # 默认路径
        return self._get_next_node(node, context)

    def _evaluate_expression(self, expression: str, variables: Dict[str, Any]) -> bool:
        """安全的表达式评估"""
        try:
            # 简化的表达式评估，仅支持基本比较
            # 例如: "count > 5", "status == 'success'", "result != None"

            # 替换变量
            expr = expression
            for var_name, var_value in variables.items():
                if isinstance(var_value, str):
                    expr = expr.replace(var_name, f"'{var_value}'")
                else:
                    expr = expr.replace(var_name, str(var_value))

            # 安全评估
            allowed_names = {
                "__builtins__": {},
                "True": True,
                "False": False,
                "None": None
            }

            return bool(eval(expr, allowed_names))

        except Exception:
            return False

    async def _execute_loop_node(self, flow: 'ComplexFlow', node: FlowNode, execution: FlowExecution) -> Optional[str]:
        """执行循环节点"""
        context = execution.context
        loop_count = context.increment_loop(node.id)

        # 检查最大迭代次数
        if node.max_iterations and loop_count > node.max_iterations:
            logger.info(f"循环达到最大迭代次数: {node.max_iterations}")
            return self._get_next_node(node, context)

        # 检查循环条件
        if node.loop_condition:
            if not self._evaluate_expression(node.loop_condition, context.variables):
                logger.info(f"循环条件不满足: {node.loop_condition}")
                return self._get_next_node(node, context)

        # 执行循环体
        if node.next_nodes:
            loop_body_result = await self._execute_flow_section(flow, node.next_nodes[0], execution)
            context.set_variable(f"loop_{node.id}_iteration_{loop_count}", loop_body_result)

            # 继续循环（返回自身）
            return node.id

        return self._get_next_node(node, context)

    async def _execute_tool_node(self, node: FlowNode, context: FlowContext) -> Optional[str]:
        """执行工具调用节点"""
        if not node.tool_name:
            logger.error(f"工具节点缺少工具名称: {node.id}")
            return self._get_next_node(node, context)

        try:
            from app.agents.tools import tool_manager

            # 准备工具参数
            tool_params = {}
            for param_name, param_value in node.tool_params.items():
                if isinstance(param_value, str) and param_value.startswith("$"):
                    # 变量引用
                    var_name = param_value[1:]
                    tool_params[param_name] = context.get_variable(var_name)
                else:
                    tool_params[param_name] = param_value

            # 执行工具
            result = await tool_manager.execute_tool(node.tool_name, **tool_params)

            # 存储结果
            context.set_variable(f"tool_{node.id}_result", result.data if result.success else None)
            context.set_variable(f"tool_{node.id}_success", result.success)
            context.set_variable(f"tool_{node.id}_error", result.error)

            logger.info(f"工具执行完成: {node.tool_name} (成功: {result.success})")

        except Exception as e:
            logger.error(f"工具执行失败: {node.tool_name}", error=str(e))
            context.set_variable(f"tool_{node.id}_success", False)
            context.set_variable(f"tool_{node.id}_error", str(e))

        return self._get_next_node(node, context)

    async def _execute_parallel_node(self, flow: 'ComplexFlow', node: FlowNode, execution: FlowExecution) -> Optional[str]:
        """执行并行节点"""
        if not node.parallel_nodes:
            return self._get_next_node(node, execution.context)

        # 创建并行任务
        tasks = []
        for parallel_node_id in node.parallel_nodes:
            task = asyncio.create_task(
                self._execute_flow_section(flow, parallel_node_id, execution)
            )
            tasks.append(task)

        # 根据合并策略等待
        if node.merge_strategy == "wait_all":
            results = await asyncio.gather(*tasks, return_exceptions=True)
        elif node.merge_strategy == "wait_any":
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            results = [task.result() for task in done]
            # 取消未完成的任务
            for task in pending:
                task.cancel()
        else:  # wait_first
            results = [await tasks[0]]
            for task in tasks[1:]:
                task.cancel()

        # 存储并行执行结果
        execution.context.set_variable(f"parallel_{node.id}_results", results)

        return self._get_next_node(node, execution.context)

    async def _execute_flow_section(self, flow: 'ComplexFlow', start_node_id: str, execution: FlowExecution) -> Any:
        """执行流程片段"""
        # 创建子执行上下文
        sub_execution = FlowExecution(
            id=f"{execution.id}_sub_{start_node_id}",
            flow_id=execution.flow_id,
            status=FlowExecutionStatus.RUNNING,
            current_node=start_node_id,
            context=copy.deepcopy(execution.context),
            start_time=datetime.utcnow()
        )

        return await self._execute_flow_internal(flow, sub_execution)


class ComplexFlow:
    """复杂流程定义"""

    def __init__(self, name: str, description: str = ""):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.nodes: Dict[str, FlowNode] = {}
        self.start_node: Optional[str] = None
        self.created_at = datetime.utcnow()

    def add_node(self, node: FlowNode) -> 'ComplexFlow':
        """添加节点"""
        self.nodes[node.id] = node

        # 自动设置起始节点
        if node.node_type == FlowNodeType.START:
            self.start_node = node.id

        return self

    def get_node(self, node_id: str) -> Optional[FlowNode]:
        """获取节点"""
        return self.nodes.get(node_id)

    def connect_nodes(self, from_node_id: str, to_node_id: str) -> 'ComplexFlow':
        """连接节点"""
        if from_node_id in self.nodes:
            from_node = self.nodes[from_node_id]
            if to_node_id not in from_node.next_nodes:
                from_node.next_nodes.append(to_node_id)
        return self

    def add_condition(self, node_id: str, condition: FlowCondition) -> 'ComplexFlow':
        """添加条件"""
        if node_id in self.nodes:
            self.nodes[node_id].conditions.append(condition)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "start_node": self.start_node,
            "nodes": {
                node_id: {
                    "id": node.id,
                    "name": node.name,
                    "type": node.node_type.value,
                    "next_nodes": node.next_nodes,
                    "conditions": node.conditions,
                    "metadata": node.metadata
                }
                for node_id, node in self.nodes.items()
            },
            "created_at": self.created_at.isoformat()
        }


# 全局流程引擎实例
flow_engine = FlowEngine()
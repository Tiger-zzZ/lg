"""
持久化工作流引擎
集成数据库持久化和执行记录管理
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.agents.workflow import FlowEngine, FlowContext, FlowExecutionStatus, FlowNode, FlowNodeType
from app.repositories.execution_repository import ExecutionRepository
from app.agents.tools import tool_manager
from app.core.error_handling import auto_retry, ErrorHandler, RetryPolicy
from app.core.metrics import get_metrics_collector, PerformanceTimer
from app.core.logging import logger


class PersistentFlowEngine(FlowEngine):
    """持久化工作流引擎"""

    def __init__(self, db: Session):
        super().__init__()
        self.db = db
        self.repository = ExecutionRepository(db)
        self.tool_manager = tool_manager
        self.error_handler = ErrorHandler()
        self.metrics = get_metrics_collector()

    async def execute_flow(
        self,
        flow_id: str,
        initial_context: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行工作流并持久化"""
        # 增加工作流执行计数
        self.metrics.increment_counter("workflow.executions.total")
        self.metrics.increment_counter(f"workflow.executions.{flow_id}")

        async with PerformanceTimer(self.metrics, f"workflow.execution.{flow_id}"):
            if flow_id not in self.flows:
                raise ValueError(f"流程不存在: {flow_id}")

            flow = self.flows[flow_id]
            start_time = datetime.utcnow()

            # 创建数据库执行记录
            db_execution = await self.repository.create_execution(
                flow_id=flow_id,
                workflow_id=workflow_id,
                user_id=user_id,
                initial_context=initial_context
            )

            execution_id = str(db_execution.id)

            try:
                # 更新状态为运行中
                await self.repository.update_execution_status(
                    execution_id, 'running', current_node=flow.start_node
                )

                await self.repository.add_log(
                    execution_id, f"开始执行工作流: {flow.name}", 'info'
                )

                # 创建内存执行上下文
                context = FlowContext()
                if initial_context:
                    context.variables.update(initial_context)

                # 执行工作流
                result = await self._execute_flow_with_persistence(
                    flow, context, execution_id, flow.start_node
                )

                # 计算执行时间
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # 更新执行结果
                await self.repository.complete_execution(
                    execution_id, result, duration_ms
                )

                await self.repository.add_log(
                    execution_id, f"工作流执行成功", 'info'
                )

                # 记录成功指标
                self.metrics.increment_counter("workflow.executions.success")
                self.metrics.record_histogram("workflow.duration_ms", duration_ms)

                logger.info(f"流程执行完成: {flow.name} (执行ID: {execution_id})")

                return {
                    "execution_id": execution_id,
                    "status": "completed",
                    "result": result,
                    "duration_ms": duration_ms,
                    "execution_path": context.execution_path
                }

            except Exception as e:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # 记录失败指标
                self.metrics.increment_counter("workflow.executions.failure")
                self.metrics.increment_counter(f"workflow.errors.{type(e).__name__}")

                # 记录失败
                await self.repository.fail_execution(
                    execution_id,
                    error_message=str(e),
                    error_details={"exception_type": type(e).__name__},
                    duration_ms=duration_ms
                )

                await self.repository.add_log(
                    execution_id, f"工作流执行失败: {str(e)}", 'error'
                )

                logger.error(f"流程执行失败: {flow.name} (执行ID: {execution_id})", error=str(e))

                return {
                    "execution_id": execution_id,
                    "status": "failed",
                    "error": str(e),
                    "duration_ms": duration_ms
                }

    async def _execute_flow_with_persistence(
        self,
        flow,
        context: FlowContext,
        execution_id: str,
        start_node_id: str
    ) -> Any:
        """带持久化的工作流执行"""
        current_node_id = start_node_id

        while current_node_id:
            context.execution_path.append(current_node_id)

            # 更新当前节点
            await self.repository.update_execution_status(
                execution_id, 'running', current_node=current_node_id
            )

            # 增加节点执行计数
            await self.repository.increment_node_executions(execution_id)

            node = flow.get_node(current_node_id)
            if not node:
                raise ValueError(f"节点不存在: {current_node_id}")

            await self.repository.add_log(
                execution_id,
                f"执行节点: {node.name}",
                'info',
                node_id=node.id,
                node_name=node.name
            )

            logger.debug(f"执行节点: {node.name} ({node.node_type.value})")

            try:
                # 执行节点
                next_node_id = await self._execute_node_with_logging(
                    flow, node, context, execution_id
                )

                # 保存上下文到数据库
                await self.repository.update_execution_context(
                    execution_id,
                    context_variables=context.variables,
                    loop_counters=context.loop_counters,
                    branch_history=context.branch_history,
                    execution_path=context.execution_path,
                    checkpoints=context.checkpoints
                )

                # 检查是否结束
                if node.node_type == FlowNodeType.END or not next_node_id:
                    break

                current_node_id = next_node_id

            except Exception as e:
                await self.repository.add_log(
                    execution_id,
                    f"节点执行失败: {str(e)}",
                    'error',
                    node_id=node.id,
                    node_name=node.name,
                    details={"exception_type": type(e).__name__}
                )
                raise

        return context.get_variable("result")

    async def _execute_node_with_logging(
        self,
        flow,
        node: FlowNode,
        context: FlowContext,
        execution_id: str
    ) -> Optional[str]:
        """执行单个节点并记录日志"""
        try:
            if node.node_type == FlowNodeType.START:
                return self._get_next_node(node, context)

            elif node.node_type == FlowNodeType.END:
                await self.repository.add_log(
                    execution_id, "到达结束节点", 'info',
                    node_id=node.id, node_name=node.name
                )
                return None

            elif node.node_type == FlowNodeType.TASK:
                if node.handler:
                    result = await node.handler(context)
                    context.set_variable(f"node_{node.id}_result", result)

                    await self.repository.add_log(
                        execution_id,
                        f"任务节点执行完成",
                        'info',
                        node_id=node.id,
                        node_name=node.name,
                        details={"result": result}
                    )
                return self._get_next_node(node, context)

            elif node.node_type == FlowNodeType.CONDITION:
                next_node = self._evaluate_condition_node(node, context)

                await self.repository.add_log(
                    execution_id,
                    f"条件判断: 下一节点={next_node}",
                    'info',
                    node_id=node.id,
                    node_name=node.name
                )
                return next_node

            elif node.node_type == FlowNodeType.LOOP:
                await self.repository.add_log(
                    execution_id,
                    f"开始循环执行",
                    'info',
                    node_id=node.id,
                    node_name=node.name
                )
                return await self._execute_loop_node(flow, node, context, execution_id)

            elif node.node_type == FlowNodeType.TOOL_CALL:
                await self.repository.add_log(
                    execution_id,
                    f"调用工具: {node.tool_name}",
                    'info',
                    node_id=node.id,
                    node_name=node.name,
                    details={"tool": node.tool_name, "params": node.tool_params}
                )
                return await self._execute_tool_node(node, context)

            elif node.node_type == FlowNodeType.PARALLEL:
                await self.repository.add_log(
                    execution_id,
                    f"开始并行执行",
                    'info',
                    node_id=node.id,
                    node_name=node.name
                )
                # 暂时返回简单的下一节点
                return self._get_next_node(node, context)

            else:
                logger.warning(f"未实现的节点类型: {node.node_type}")
                return self._get_next_node(node, context)

        except Exception as e:
            logger.error(f"节点执行失败: {node.name}", error=str(e))
            raise

    async def _execute_loop_node(
        self,
        flow,
        node: FlowNode,
        context: FlowContext,
        execution_id: str
    ) -> Optional[str]:
        """执行循环节点"""
        loop_count = context.increment_loop(node.id)

        await self.repository.add_log(
            execution_id,
            f"循环迭代: 第 {loop_count} 次",
            'debug',
            node_id=node.id,
            node_name=node.name
        )

        # 检查最大迭代次数
        if node.max_iterations and loop_count > node.max_iterations:
            await self.repository.add_log(
                execution_id,
                f"达到最大迭代次数: {node.max_iterations}",
                'warning',
                node_id=node.id,
                node_name=node.name
            )
            return self._get_next_node(node, context)

        # 检查循环条件
        if node.loop_condition:
            should_continue = self._evaluate_expression(
                node.loop_condition, context.variables
            )

            if not should_continue:
                await self.repository.add_log(
                    execution_id,
                    "循环条件不满足,退出循环",
                    'info',
                    node_id=node.id,
                    node_name=node.name
                )
                return self._get_next_node(node, context)

            # 继续循环 - 执行循环体
            if node.next_nodes:
                return node.next_nodes[0]

        return self._get_next_node(node, context)

    @auto_retry(max_attempts=3, retryable_exceptions=(ConnectionError, TimeoutError))
    async def _execute_tool_node(
        self,
        node: FlowNode,
        context: FlowContext
    ) -> Optional[str]:
        """执行工具调用节点"""
        tool_name = node.tool_name
        tool_params = node.tool_params or {}

        # 从上下文中解析参数
        resolved_params = {}
        for key, value in tool_params.items():
            if isinstance(value, str) and value.startswith("$"):
                # 从上下文变量中获取值
                var_name = value[1:]
                resolved_params[key] = context.get_variable(var_name)
            else:
                resolved_params[key] = value

        logger.info(f"执行工具: {tool_name}", params=resolved_params)

        # 执行工具
        try:
            result = await self.tool_manager.execute_tool(tool_name, **resolved_params)

            # 保存结果到上下文
            context.set_variable(f"tool_{tool_name}_result", result.data)
            context.set_variable(f"tool_{tool_name}_success", result.success)

            if not result.success:
                logger.warning(f"工具执行失败: {tool_name}", error=result.error)
                context.set_variable(f"tool_{tool_name}_error", result.error)

            return self._get_next_node(node, context)

        except Exception as e:
            logger.error(f"工具执行异常: {tool_name}", error=str(e))
            await self.error_handler.handle_error(e, {"tool": tool_name, "params": resolved_params})
            raise

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """获取执行状态"""
        execution = await self.repository.get_execution(execution_id)
        if execution:
            return execution.to_dict()
        return None

    async def get_execution_logs(self, execution_id: str, log_level: Optional[str] = None):
        """获取执行日志"""
        logs = await self.repository.get_logs(execution_id, log_level)
        return [log.to_dict() for log in logs]

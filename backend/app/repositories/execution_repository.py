"""工作流执行持久化存储"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from app.models.workflow import FlowExecution, ExecutionLog
from app.core.logging import logger


class ExecutionRepository:
    """工作流执行记录存储"""

    def __init__(self, db: Session):
        self.db = db

    async def create_execution(
        self,
        flow_id: str,
        workflow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> FlowExecution:
        """创建新的执行记录"""
        execution = FlowExecution(
            id=uuid.uuid4(),
            flow_id=flow_id,
            workflow_id=uuid.UUID(workflow_id) if workflow_id else None,
            user_id=uuid.UUID(user_id) if user_id else None,
            status='pending',
            context_variables=initial_context or {},
            loop_counters={},
            branch_history=[],
            execution_path=[],
            checkpoints={},
            node_executions=0
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        logger.info(f"Created execution record: {execution.id}")
        return execution

    async def update_execution(
        self,
        execution_id: str,
        **updates
    ) -> Optional[FlowExecution]:
        """更新执行记录"""
        execution = self.db.query(FlowExecution).filter(
            FlowExecution.id == uuid.UUID(execution_id)
        ).first()

        if not execution:
            logger.warning(f"Execution not found: {execution_id}")
            return None

        for key, value in updates.items():
            if hasattr(execution, key):
                setattr(execution, key, value)

        execution.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(execution)

        return execution

    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        current_node: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[FlowExecution]:
        """更新执行状态"""
        updates = {"status": status}

        if current_node:
            updates["current_node"] = current_node

        if error_message:
            updates["error_message"] = error_message
            updates["error_details"] = error_details

        if status in ['completed', 'failed', 'cancelled']:
            updates["completed_at"] = datetime.utcnow()

        return await self.update_execution(execution_id, **updates)

    async def update_execution_context(
        self,
        execution_id: str,
        context_variables: Optional[Dict[str, Any]] = None,
        loop_counters: Optional[Dict[str, int]] = None,
        branch_history: Optional[List[str]] = None,
        execution_path: Optional[List[str]] = None,
        checkpoints: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Optional[FlowExecution]:
        """更新执行上下文"""
        updates = {}

        if context_variables is not None:
            updates["context_variables"] = context_variables
        if loop_counters is not None:
            updates["loop_counters"] = loop_counters
        if branch_history is not None:
            updates["branch_history"] = branch_history
        if execution_path is not None:
            updates["execution_path"] = execution_path
        if checkpoints is not None:
            updates["checkpoints"] = checkpoints

        return await self.update_execution(execution_id, **updates)

    async def increment_node_executions(self, execution_id: str) -> Optional[FlowExecution]:
        """增加节点执行计数"""
        execution = self.db.query(FlowExecution).filter(
            FlowExecution.id == uuid.UUID(execution_id)
        ).first()

        if execution:
            execution.node_executions += 1
            self.db.commit()
            self.db.refresh(execution)

        return execution

    async def complete_execution(
        self,
        execution_id: str,
        result: Any,
        duration_ms: float
    ) -> Optional[FlowExecution]:
        """完成执行"""
        return await self.update_execution(
            execution_id,
            status='completed',
            result=result,
            duration_ms=duration_ms,
            completed_at=datetime.utcnow()
        )

    async def fail_execution(
        self,
        execution_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None
    ) -> Optional[FlowExecution]:
        """标记执行失败"""
        updates = {
            "status": 'failed',
            "error_message": error_message,
            "error_details": error_details,
            "completed_at": datetime.utcnow()
        }

        if duration_ms:
            updates["duration_ms"] = duration_ms

        return await self.update_execution(execution_id, **updates)

    async def get_execution(self, execution_id: str) -> Optional[FlowExecution]:
        """获取执行记录"""
        return self.db.query(FlowExecution).filter(
            FlowExecution.id == uuid.UUID(execution_id)
        ).first()

    async def list_executions(
        self,
        flow_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[FlowExecution]:
        """查询执行记录列表"""
        query = self.db.query(FlowExecution)

        if flow_id:
            query = query.filter(FlowExecution.flow_id == flow_id)
        if user_id:
            query = query.filter(FlowExecution.user_id == uuid.UUID(user_id))
        if status:
            query = query.filter(FlowExecution.status == status)

        return query.order_by(desc(FlowExecution.started_at)).limit(limit).offset(offset).all()

    async def add_log(
        self,
        execution_id: str,
        message: str,
        log_level: str = 'info',
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> ExecutionLog:
        """添加执行日志"""
        log = ExecutionLog(
            id=uuid.uuid4(),
            execution_id=uuid.UUID(execution_id),
            node_id=node_id,
            node_name=node_name,
            log_level=log_level,
            message=message,
            details=details
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    async def get_logs(
        self,
        execution_id: str,
        log_level: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionLog]:
        """获取执行日志"""
        query = self.db.query(ExecutionLog).filter(
            ExecutionLog.execution_id == uuid.UUID(execution_id)
        )

        if log_level:
            query = query.filter(ExecutionLog.log_level == log_level)

        return query.order_by(ExecutionLog.created_at).limit(limit).all()

    async def delete_execution(self, execution_id: str) -> bool:
        """删除执行记录"""
        execution = await self.get_execution(execution_id)
        if execution:
            # 删除关联的日志
            self.db.query(ExecutionLog).filter(
                ExecutionLog.execution_id == uuid.UUID(execution_id)
            ).delete()

            # 删除执行记录
            self.db.delete(execution)
            self.db.commit()
            return True
        return False
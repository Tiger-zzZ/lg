"""
工作流管理API
提供复杂状态流转的管理接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.workflow import flow_engine, FlowExecutionStatus
from app.agents.workflow.agent import WorkflowAgent, DataAnalysisWorkflowAgent
from app.api.auth import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


class WorkflowCreateRequest(BaseModel):
    """工作流创建请求"""
    name: str
    description: str = ""
    agent_type: str = "workflow"  # workflow, data_analysis


class WorkflowExecuteRequest(BaseModel):
    """工作流执行请求"""
    workflow_id: Optional[str] = None
    agent_id: Optional[str] = None
    initial_context: Dict[str, Any] = {}


class FlowExecutionResponse(BaseModel):
    """流程执行响应"""
    execution_id: str
    flow_id: str
    status: str
    current_node: str
    start_time: str
    end_time: Optional[str] = None
    result: Any = None
    error_message: Optional[str] = None


# 全局Agent实例管理
workflow_agents: Dict[str, WorkflowAgent] = {}


@router.post("/workflows/agents", response_model=Dict[str, Any])
async def create_workflow_agent(
    request: WorkflowCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建工作流Agent"""
    try:
        if request.agent_type == "data_analysis":
            agent = DataAnalysisWorkflowAgent()
        else:
            agent = WorkflowAgent(request.name, request.description)

        workflow_agents[agent.id] = agent

        logger.info(f"创建工作流Agent: {agent.name} (ID: {agent.id})")

        return {
            "agent_id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "type": request.agent_type,
            "workflows": agent.list_workflows(),
            "enabled_tools": agent.enabled_tools
        }

    except Exception as e:
        logger.error(f"创建工作流Agent失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建Agent失败: {str(e)}")


@router.get("/workflows/agents")
async def list_workflow_agents(current_user: User = Depends(get_current_user)):
    """列出所有工作流Agent"""
    try:
        agents_info = []
        for agent_id, agent in workflow_agents.items():
            agents_info.append({
                "agent_id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "workflow_count": len(agent.workflows),
                "default_workflow": agent.default_workflow,
                "enabled_tools": agent.enabled_tools
            })

        return {"agents": agents_info, "total_count": len(agents_info)}

    except Exception as e:
        logger.error(f"列出工作流Agent失败: {e}")
        raise HTTPException(status_code=500, detail="获取Agent列表失败")


@router.post("/workflows/execute", response_model=FlowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user)
):
    """执行工作流"""
    try:
        # 获取Agent
        if request.agent_id and request.agent_id in workflow_agents:
            agent = workflow_agents[request.agent_id]
        else:
            # 使用默认的数据分析Agent
            if "default_data_analysis" not in workflow_agents:
                workflow_agents["default_data_analysis"] = DataAnalysisWorkflowAgent()
            agent = workflow_agents["default_data_analysis"]

        # 执行工作流
        if request.workflow_id:
            execution = await flow_engine.execute_flow(request.workflow_id, request.initial_context)
        else:
            result = await agent.execute_workflow(initial_context=request.initial_context)
            # 获取最近的执行记录
            executions = list(flow_engine.executions.values())
            execution = executions[-1] if executions else None

        if not execution:
            raise HTTPException(status_code=500, detail="无法获取执行结果")

        return FlowExecutionResponse(
            execution_id=execution.id,
            flow_id=execution.flow_id,
            status=execution.status.value,
            current_node=execution.current_node,
            start_time=execution.start_time.isoformat(),
            end_time=execution.end_time.isoformat() if execution.end_time else None,
            result=execution.result,
            error_message=execution.error_message
        )

    except Exception as e:
        logger.error(f"执行工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")


@router.get("/workflows/{workflow_id}")
async def get_workflow_info(
    workflow_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取工作流信息"""
    try:
        if workflow_id not in flow_engine.flows:
            raise HTTPException(status_code=404, detail="工作流不存在")

        workflow = flow_engine.flows[workflow_id]
        return workflow.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工作流信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取工作流信息失败")


@router.get("/workflows")
async def list_workflows(current_user: User = Depends(get_current_user)):
    """列出所有工作流"""
    try:
        workflows = []
        for flow_id, flow in flow_engine.flows.items():
            workflows.append({
                "id": flow.id,
                "name": flow.name,
                "description": flow.description,
                "node_count": len(flow.nodes),
                "start_node": flow.start_node,
                "created_at": flow.created_at.isoformat()
            })

        return {"workflows": workflows, "total_count": len(workflows)}

    except Exception as e:
        logger.error(f"列出工作流失败: {e}")
        raise HTTPException(status_code=500, detail="获取工作流列表失败")


@router.get("/executions")
async def list_executions(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """列出执行记录"""
    try:
        executions = list(flow_engine.executions.values())

        # 状态过滤
        if status:
            try:
                filter_status = FlowExecutionStatus(status)
                executions = [e for e in executions if e.status == filter_status]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的状态: {status}")

        # 按时间排序并限制数量
        executions.sort(key=lambda x: x.start_time, reverse=True)
        executions = executions[:limit]

        execution_list = []
        for execution in executions:
            execution_list.append({
                "execution_id": execution.id,
                "flow_id": execution.flow_id,
                "status": execution.status.value,
                "current_node": execution.current_node,
                "start_time": execution.start_time.isoformat(),
                "end_time": execution.end_time.isoformat() if execution.end_time else None,
                "duration": (
                    (execution.end_time - execution.start_time).total_seconds()
                    if execution.end_time else None
                ),
                "has_result": execution.result is not None,
                "has_error": execution.error_message is not None
            })

        return {"executions": execution_list, "total_count": len(execution_list)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出执行记录失败: {e}")
        raise HTTPException(status_code=500, detail="获取执行记录失败")


@router.get("/executions/{execution_id}")
async def get_execution_details(
    execution_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取执行详情"""
    try:
        if execution_id not in flow_engine.executions:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        execution = flow_engine.executions[execution_id]

        return {
            "execution_id": execution.id,
            "flow_id": execution.flow_id,
            "status": execution.status.value,
            "current_node": execution.current_node,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "result": execution.result,
            "error_message": execution.error_message,
            "context": {
                "variables": execution.context.variables,
                "execution_path": execution.context.execution_path,
                "branch_history": execution.context.branch_history,
                "loop_counters": execution.context.loop_counters
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取执行详情失败")


@router.get("/agents/{agent_id}/workflows")
async def get_agent_workflows(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取Agent的工作流列表"""
    try:
        if agent_id not in workflow_agents:
            raise HTTPException(status_code=404, detail="Agent不存在")

        agent = workflow_agents[agent_id]
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "workflows": agent.list_workflows()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取Agent工作流失败: {e}")
        raise HTTPException(status_code=500, detail="获取工作流失败")
"""
提示模板API路由
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.prompts import PromptTemplate, PromptManager, prompt_manager, PromptType
from app.api.auth import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


class PromptTemplateCreate(BaseModel):
    """创建提示模板请求"""
    name: str
    description: str
    template: str
    prompt_type: str
    variables: List[Dict[str, Any]] = []
    tags: List[str] = []


class PromptTemplateResponse(BaseModel):
    """提示模板响应"""
    id: str
    name: str
    description: str
    template: str
    prompt_type: str
    variables: List[Dict[str, Any]]
    tags: List[str]
    version: str
    usage_count: int


class PromptRenderRequest(BaseModel):
    """提示渲染请求"""
    template_id: str
    context: Dict[str, Any]


class PromptRenderResponse(BaseModel):
    """提示渲染响应"""
    rendered_prompt: str
    template_id: str
    context_used: Dict[str, Any]


@router.get("/templates", response_model=List[PromptTemplateResponse])
async def list_templates(
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """获取提示模板列表"""
    try:
        tag_list = tags.split(",") if tags else None
        templates = prompt_manager.list_templates(tags=tag_list)

        return [
            PromptTemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                template=t.template,
                prompt_type=t.prompt_type.value,
                variables=[
                    {
                        "name": v.name,
                        "type": v.type,
                        "description": v.description,
                        "required": v.required,
                        "default_value": v.default_value,
                        "validation_pattern": v.validation_pattern
                    }
                    for v in t.variables
                ],
                tags=t.tags,
                version=t.version,
                usage_count=t.usage_count
            )
            for t in templates
        ]

    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模板列表失败")


@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取特定提示模板"""
    try:
        template = prompt_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        return PromptTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            template=template.template,
            prompt_type=template.prompt_type.value,
            variables=[
                {
                    "name": v.name,
                    "type": v.type,
                    "description": v.description,
                    "required": v.required,
                    "default_value": v.default_value,
                    "validation_pattern": v.validation_pattern
                }
                for v in template.variables
            ],
            tags=template.tags,
            version=template.version,
            usage_count=template.usage_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise HTTPException(status_code=500, detail="获取模板失败")


@router.post("/templates/render", response_model=PromptRenderResponse)
async def render_template(
    request: PromptRenderRequest,
    current_user: User = Depends(get_current_user)
):
    """渲染提示模板"""
    try:
        rendered = prompt_manager.render_template(request.template_id, request.context)

        return PromptRenderResponse(
            rendered_prompt=rendered,
            template_id=request.template_id,
            context_used=request.context
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"渲染模板失败: {e}")
        raise HTTPException(status_code=500, detail="渲染模板失败")


@router.get("/templates/search/{keyword}")
async def search_templates(
    keyword: str,
    current_user: User = Depends(get_current_user)
):
    """搜索提示模板"""
    try:
        templates = prompt_manager.search_templates(keyword)

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "tags": t.tags,
                "usage_count": t.usage_count
            }
            for t in templates
        ]

    except Exception as e:
        logger.error(f"搜索模板失败: {e}")
        raise HTTPException(status_code=500, detail="搜索模板失败")


@router.get("/templates/stats")
async def get_template_stats(
    current_user: User = Depends(get_current_user)
):
    """获取模板统计信息"""
    try:
        return prompt_manager.get_template_stats()

    except Exception as e:
        logger.error(f"获取模板统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取模板统计失败")


@router.post("/templates/create", response_model=PromptTemplateResponse)
async def create_template(
    request: PromptTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """创建自定义提示模板"""
    try:
        # 验证提示类型
        try:
            prompt_type = PromptType(request.prompt_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的提示类型: {request.prompt_type}"
            )

        # 创建模板
        from app.agents.prompts.template import PromptVariable
        import uuid

        variables = []
        for var_data in request.variables:
            variables.append(PromptVariable(
                name=var_data["name"],
                type=var_data["type"],
                description=var_data["description"],
                required=var_data.get("required", True),
                default_value=var_data.get("default_value"),
                validation_pattern=var_data.get("validation_pattern")
            ))

        template = PromptTemplate(
            id=f"custom_{uuid.uuid4().hex[:8]}",
            name=request.name,
            description=request.description,
            template=request.template,
            prompt_type=prompt_type,
            variables=variables,
            tags=request.tags + ["自定义"]
        )

        prompt_manager.register_template(template)

        return PromptTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            template=template.template,
            prompt_type=template.prompt_type.value,
            variables=[
                {
                    "name": v.name,
                    "type": v.type,
                    "description": v.description,
                    "required": v.required,
                    "default_value": v.default_value,
                    "validation_pattern": v.validation_pattern
                }
                for v in template.variables
            ],
            tags=template.tags,
            version=template.version,
            usage_count=template.usage_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        raise HTTPException(status_code=500, detail="创建模板失败")
"""
高级提示模板系统
支持动态提示生成、变量替换、上下文感知
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from enum import Enum
from app.core.logging import logger


class PromptType(Enum):
    """提示类型枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    INSTRUCTION = "instruction"
    CONTEXT = "context"


@dataclass
class PromptVariable:
    """提示变量定义"""
    name: str
    type: str  # string, number, boolean, list, dict
    description: str
    required: bool = True
    default_value: Any = None
    validation_pattern: Optional[str] = None


@dataclass
class PromptTemplate:
    """提示模板类"""
    id: str
    name: str
    description: str
    template: str
    prompt_type: PromptType
    variables: List[PromptVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    usage_count: int = 0

    def validate_variables(self, context: Dict[str, Any]) -> List[str]:
        """验证变量"""
        errors = []

        for var in self.variables:
            if var.required and var.name not in context:
                errors.append(f"必需变量 '{var.name}' 缺失")
                continue

            if var.name in context:
                value = context[var.name]

                # 类型验证
                if var.type == "string" and not isinstance(value, str):
                    errors.append(f"变量 '{var.name}' 必须是字符串类型")
                elif var.type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"变量 '{var.name}' 必须是数字类型")
                elif var.type == "boolean" and not isinstance(value, bool):
                    errors.append(f"变量 '{var.name}' 必须是布尔类型")
                elif var.type == "list" and not isinstance(value, list):
                    errors.append(f"变量 '{var.name}' 必须是列表类型")
                elif var.type == "dict" and not isinstance(value, dict):
                    errors.append(f"变量 '{var.name}' 必须是字典类型")

                # 正则验证
                if var.validation_pattern and isinstance(value, str):
                    if not re.match(var.validation_pattern, value):
                        errors.append(f"变量 '{var.name}' 不符合验证模式")

        return errors

    def render(self, context: Dict[str, Any]) -> str:
        """渲染模板"""
        # 验证变量
        errors = self.validate_variables(context)
        if errors:
            raise ValueError(f"模板验证失败: {', '.join(errors)}")

        # 添加默认值
        render_context = context.copy()
        for var in self.variables:
            if var.name not in render_context and var.default_value is not None:
                render_context[var.name] = var.default_value

        # 渲染模板
        try:
            rendered = self.template.format(**render_context)
            self.usage_count += 1
            return rendered
        except KeyError as e:
            raise ValueError(f"模板渲染失败，缺少变量: {e}")
        except Exception as e:
            raise ValueError(f"模板渲染失败: {e}")


class PromptManager:
    """提示模板管理器"""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """加载默认模板"""
        # 通用对话模板
        self.register_template(PromptTemplate(
            id="general_chat",
            name="通用对话",
            description="通用AI助手对话模板",
            template="你是一个专业的AI助手。用户问题：{user_input}\n\n请提供有帮助的回答。",
            prompt_type=PromptType.SYSTEM,
            variables=[
                PromptVariable("user_input", "string", "用户输入的问题")
            ],
            tags=["通用", "对话"]
        ))

        # 代码分析模板
        self.register_template(PromptTemplate(
            id="code_analysis",
            name="代码分析",
            description="代码分析和优化建议模板",
            template="""你是一个专业的代码分析师。

代码语言：{language}
代码内容：
```{language}
{code}
```

分析要求：{analysis_type}

请提供详细的分析报告，包括：
1. 代码质量评估
2. 潜在问题识别
3. 优化建议
4. 最佳实践建议""",
            prompt_type=PromptType.INSTRUCTION,
            variables=[
                PromptVariable("language", "string", "编程语言"),
                PromptVariable("code", "string", "要分析的代码"),
                PromptVariable("analysis_type", "string", "分析类型", default_value="全面分析")
            ],
            tags=["编程", "分析", "代码"]
        ))

        # 数据分析模板
        self.register_template(PromptTemplate(
            id="data_analysis",
            name="数据分析",
            description="数据分析和可视化模板",
            template="""你是一个专业的数据分析师。

数据描述：{data_description}
分析目标：{analysis_goal}
数据格式：{data_format}

{context_data}

请进行以下分析：
1. 数据概览和基本统计
2. 数据质量评估
3. 关键洞察和趋势
4. 可视化建议
5. 结论和建议

分析深度：{depth_level}""",
            prompt_type=PromptType.INSTRUCTION,
            variables=[
                PromptVariable("data_description", "string", "数据描述"),
                PromptVariable("analysis_goal", "string", "分析目标"),
                PromptVariable("data_format", "string", "数据格式", default_value="CSV"),
                PromptVariable("context_data", "string", "上下文数据"),
                PromptVariable("depth_level", "string", "分析深度", default_value="标准分析")
            ],
            tags=["数据", "分析", "统计"]
        ))

        # 文档问答模板
        self.register_template(PromptTemplate(
            id="document_qa",
            name="文档问答",
            description="基于文档的问答模板",
            template="""基于以下文档内容回答用户问题：

相关文档片段：
{document_context}

用户问题：{user_question}

回答要求：
- 基于文档内容回答
- 如果文档中没有相关信息，请明确说明
- 提供准确、详细的回答
- 引用相关的文档片段

置信度要求：{confidence_level}""",
            prompt_type=PromptType.SYSTEM,
            variables=[
                PromptVariable("document_context", "string", "文档上下文"),
                PromptVariable("user_question", "string", "用户问题"),
                PromptVariable("confidence_level", "string", "置信度要求", default_value="高置信度")
            ],
            tags=["文档", "问答", "RAG"]
        ))

        logger.info(f"已加载 {len(self._templates)} 个默认模板")

    def register_template(self, template: PromptTemplate):
        """注册模板"""
        self._templates[template.id] = template
        logger.info(f"注册模板: {template.name} (ID: {template.id})")

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self._templates.get(template_id)

    def list_templates(self, tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """列出模板"""
        templates = list(self._templates.values())

        if tags:
            templates = [
                t for t in templates
                if any(tag in t.tags for tag in tags)
            ]

        return sorted(templates, key=lambda x: x.created_at, reverse=True)

    def search_templates(self, keyword: str) -> List[PromptTemplate]:
        """搜索模板"""
        keyword = keyword.lower()
        results = []

        for template in self._templates.values():
            if (keyword in template.name.lower() or
                keyword in template.description.lower() or
                any(keyword in tag.lower() for tag in template.tags)):
                results.append(template)

        return sorted(results, key=lambda x: x.usage_count, reverse=True)

    def render_template(self, template_id: str, context: Dict[str, Any]) -> str:
        """渲染模板"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        return template.render(context)

    def get_template_stats(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        total_templates = len(self._templates)
        total_usage = sum(t.usage_count for t in self._templates.values())

        # 按标签统计
        tag_counts = {}
        for template in self._templates.values():
            for tag in template.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # 最常用模板
        most_used = sorted(
            self._templates.values(),
            key=lambda x: x.usage_count,
            reverse=True
        )[:5]

        return {
            "total_templates": total_templates,
            "total_usage": total_usage,
            "tag_distribution": tag_counts,
            "most_used_templates": [
                {"id": t.id, "name": t.name, "usage_count": t.usage_count}
                for t in most_used
            ]
        }

    def export_templates(self) -> Dict[str, Any]:
        """导出模板"""
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "template": t.template,
                    "prompt_type": t.prompt_type.value,
                    "variables": [
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
                    "tags": t.tags,
                    "version": t.version
                }
                for t in self._templates.values()
            ]
        }

    def import_templates(self, data: Dict[str, Any]):
        """导入模板"""
        imported_count = 0

        for template_data in data.get("templates", []):
            try:
                variables = [
                    PromptVariable(**var_data)
                    for var_data in template_data.get("variables", [])
                ]

                template = PromptTemplate(
                    id=template_data["id"],
                    name=template_data["name"],
                    description=template_data["description"],
                    template=template_data["template"],
                    prompt_type=PromptType(template_data["prompt_type"]),
                    variables=variables,
                    tags=template_data.get("tags", []),
                    version=template_data.get("version", "1.0")
                )

                self.register_template(template)
                imported_count += 1

            except Exception as e:
                logger.error(f"导入模板失败: {e}")

        logger.info(f"成功导入 {imported_count} 个模板")
        return imported_count


# 全局模板管理器实例
prompt_manager = PromptManager()
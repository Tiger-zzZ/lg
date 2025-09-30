"""
Agent工具具体实现
包含各种常用的外部工具
"""

import json
import math
import statistics
from typing import Dict, Any, List, Optional
import asyncio
import os
from sqlalchemy import text

from app.core.database import SessionLocal
from app.core.logging import logger
from . import BaseTool, ToolResult, ToolType


class CalculatorTool(BaseTool):
    """计算器工具"""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算，支持基本运算和统计函数",
            tool_type=ToolType.CALCULATION
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "expression": {
                "type": "string",
                "description": "要计算的数学表达式，如 '2+3*4' 或 'sqrt(16)'"
            },
            "data": {
                "type": "array",
                "description": "用于统计计算的数字列表，可选",
                "items": {"type": "number"}
            },
            "operation": {
                "type": "string",
                "description": "统计操作类型：mean, median, mode, std, var",
                "enum": ["mean", "median", "mode", "std", "var"]
            }
        }

    async def execute(self, expression: str = None, data: List[float] = None,
                     operation: str = None, **kwargs) -> ToolResult:
        """执行计算"""
        try:
            if data and operation:
                # 统计计算
                if operation == "mean":
                    result = statistics.mean(data)
                elif operation == "median":
                    result = statistics.median(data)
                elif operation == "mode":
                    result = statistics.mode(data)
                elif operation == "std":
                    result = statistics.stdev(data) if len(data) > 1 else 0
                elif operation == "var":
                    result = statistics.variance(data) if len(data) > 1 else 0
                else:
                    return ToolResult(success=False, error=f"不支持的统计操作: {operation}")

                return ToolResult(
                    success=True,
                    data={"result": result, "operation": operation, "data_count": len(data)}
                )

            elif expression:
                # 数学表达式计算
                # 支持的函数
                safe_dict = {
                    "abs": abs, "round": round, "min": min, "max": max,
                    "sum": sum, "pow": pow,
                    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
                    "log": math.log, "log10": math.log10, "exp": math.exp,
                    "pi": math.pi, "e": math.e
                }

                # 安全计算
                result = eval(expression, {"__builtins__": {}}, safe_dict)

                return ToolResult(
                    success=True,
                    data={"result": result, "expression": expression}
                )
            else:
                return ToolResult(success=False, error="需要提供expression或data+operation参数")

        except Exception as e:
            return ToolResult(success=False, error=f"计算错误: {str(e)}")


class WebSearchTool(BaseTool):
    """网络搜索工具（模拟实现）"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="搜索网络信息",
            tool_type=ToolType.WEB_SEARCH
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "搜索查询词"
            },
            "max_results": {
                "type": "integer",
                "description": "最大结果数量",
                "default": 10
            }
        }

    async def execute(self, query: str, max_results: int = 10, **kwargs) -> ToolResult:
        """执行搜索"""
        try:
            # 模拟搜索延迟
            await asyncio.sleep(0.5)

            # 模拟搜索结果
            mock_results = [
                {
                    "title": f"搜索结果 {i+1}: {query}",
                    "url": f"https://example.com/result-{i+1}",
                    "snippet": f"这是关于 '{query}' 的搜索结果内容摘要 {i+1}",
                    "relevance_score": round(0.9 - i*0.1, 2)
                }
                for i in range(min(max_results, 5))
            ]

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": mock_results,
                    "total_found": len(mock_results)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=f"搜索失败: {str(e)}")


class FileReadTool(BaseTool):
    """文件读取工具"""

    def __init__(self):
        super().__init__(
            name="file_reader",
            description="读取和分析文件内容",
            tool_type=ToolType.FILE_OPERATION
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "file_path": {
                "type": "string",
                "description": "要读取的文件路径"
            },
            "encoding": {
                "type": "string",
                "description": "文件编码",
                "default": "utf-8"
            },
            "max_lines": {
                "type": "integer",
                "description": "最大读取行数",
                "default": 1000
            }
        }

    async def execute(self, file_path: str, encoding: str = "utf-8",
                     max_lines: int = 1000, **kwargs) -> ToolResult:
        """读取文件"""
        try:
            if not os.path.exists(file_path):
                return ToolResult(success=False, error=f"文件不存在: {file_path}")

            # 安全检查：限制文件路径
            if ".." in file_path or file_path.startswith("/"):
                return ToolResult(success=False, error="不安全的文件路径")

            # 使用同步文件读取
            with open(file_path, 'r', encoding=encoding) as f:
                lines = []
                line_count = 0
                for line in f:
                    if line_count >= max_lines:
                        break
                    lines.append(line.rstrip('\n\r'))
                    line_count += 1

            file_stats = os.stat(file_path)

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "content": lines,
                    "line_count": len(lines),
                    "file_size": file_stats.st_size,
                    "truncated": line_count >= max_lines
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=f"文件读取失败: {str(e)}")


class DataProcessingTool(BaseTool):
    """数据处理工具"""

    def __init__(self):
        super().__init__(
            name="data_processor",
            description="处理和分析JSON数据",
            tool_type=ToolType.DATA_PROCESSING
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "data": {
                "type": "object",
                "description": "要处理的数据"
            },
            "operation": {
                "type": "string",
                "description": "处理操作",
                "enum": ["filter", "transform", "aggregate", "validate"]
            },
            "config": {
                "type": "object",
                "description": "操作配置参数"
            }
        }

    async def execute(self, data: Any, operation: str, config: Dict[str, Any] = None,
                     **kwargs) -> ToolResult:
        """处理数据"""
        try:
            config = config or {}

            if operation == "filter":
                # 数据过滤
                if isinstance(data, list):
                    field = config.get("field")
                    value = config.get("value")
                    operator = config.get("operator", "eq")

                    if field and value is not None:
                        if operator == "eq":
                            result = [item for item in data if item.get(field) == value]
                        elif operator == "gt":
                            result = [item for item in data if item.get(field, 0) > value]
                        elif operator == "lt":
                            result = [item for item in data if item.get(field, 0) < value]
                        else:
                            result = data
                    else:
                        result = data
                else:
                    result = data

            elif operation == "transform":
                # 数据转换
                if isinstance(data, list):
                    field_mapping = config.get("field_mapping", {})
                    result = []
                    for item in data:
                        new_item = {}
                        for old_field, new_field in field_mapping.items():
                            if old_field in item:
                                new_item[new_field] = item[old_field]
                        result.append(new_item)
                else:
                    result = data

            elif operation == "aggregate":
                # 数据聚合
                if isinstance(data, list):
                    field = config.get("field")
                    agg_type = config.get("type", "count")

                    if agg_type == "count":
                        result = {"count": len(data)}
                    elif agg_type == "sum" and field:
                        values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
                        result = {"sum": sum(values), "field": field}
                    elif agg_type == "avg" and field:
                        values = [item.get(field, 0) for item in data if isinstance(item.get(field), (int, float))]
                        result = {"avg": sum(values) / len(values) if values else 0, "field": field}
                    else:
                        result = {"count": len(data)}
                else:
                    result = {"error": "聚合操作需要列表数据"}

            elif operation == "validate":
                # 数据验证
                schema = config.get("schema", {})
                errors = []

                if isinstance(data, dict):
                    for field, field_type in schema.items():
                        if field not in data:
                            errors.append(f"缺少字段: {field}")
                        elif not isinstance(data[field], eval(field_type)):
                            errors.append(f"字段类型错误: {field} 应为 {field_type}")

                result = {
                    "valid": len(errors) == 0,
                    "errors": errors
                }

            else:
                return ToolResult(success=False, error=f"不支持的操作: {operation}")

            return ToolResult(
                success=True,
                data={
                    "operation": operation,
                    "result": result,
                    "original_count": len(data) if isinstance(data, list) else 1
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=f"数据处理失败: {str(e)}")


class DatabaseQueryTool(BaseTool):
    """数据库查询工具"""

    def __init__(self):
        super().__init__(
            name="database_query",
            description="执行安全的数据库查询",
            tool_type=ToolType.DATABASE_QUERY
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "query_type": {
                "type": "string",
                "description": "查询类型",
                "enum": ["select", "count", "aggregate"]
            },
            "table": {
                "type": "string",
                "description": "表名"
            },
            "conditions": {
                "type": "object",
                "description": "查询条件"
            },
            "limit": {
                "type": "integer",
                "description": "结果限制",
                "default": 100
            }
        }

    async def execute(self, query_type: str, table: str, conditions: Dict[str, Any] = None,
                     limit: int = 100, **kwargs) -> ToolResult:
        """执行数据库查询"""
        try:
            # 安全的表名白名单
            allowed_tables = ["documents", "agents", "users", "agent_memories"]
            if table not in allowed_tables:
                return ToolResult(success=False, error=f"不允许访问表: {table}")

            db = SessionLocal()
            conditions = conditions or {}

            if query_type == "count":
                query = f"SELECT COUNT(*) as count FROM {table}"
                where_clause = " WHERE " + " AND ".join([f"{k} = :{k}" for k in conditions.keys()]) if conditions else ""
                query += where_clause

                result = db.execute(text(query), conditions).fetchone()
                data = {"count": result.count}

            elif query_type == "select":
                query = f"SELECT * FROM {table}"
                where_clause = " WHERE " + " AND ".join([f"{k} = :{k}" for k in conditions.keys()]) if conditions else ""
                query += where_clause + f" LIMIT {limit}"

                result = db.execute(text(query), conditions).fetchall()
                data = {"rows": [dict(row._mapping) for row in result], "count": len(result)}

            elif query_type == "aggregate":
                # 简单聚合查询
                query = f"SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(created_at) as latest FROM {table}"
                where_clause = " WHERE " + " AND ".join([f"{k} = :{k}" for k in conditions.keys()]) if conditions else ""
                query += where_clause

                result = db.execute(text(query), conditions).fetchone()
                data = {
                    "count": result.count,
                    "earliest": result.earliest.isoformat() if result.earliest else None,
                    "latest": result.latest.isoformat() if result.latest else None
                }

            else:
                return ToolResult(success=False, error=f"不支持的查询类型: {query_type}")

            db.close()

            return ToolResult(
                success=True,
                data={
                    "query_type": query_type,
                    "table": table,
                    "result": data
                }
            )

        except Exception as e:
            if 'db' in locals():
                db.close()
            return ToolResult(success=False, error=f"数据库查询失败: {str(e)}")
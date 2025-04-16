import operator
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import jsonschema
import asyncio
import json
import inspect
import traceback

def agent_operation(func,description="",is_mcp_tool=True):
    func.is_mcp_tool = is_mcp_tool
    func.description = description
    return func

class StrategyExecAgent(ABC):
    """
    MCP 标准 ToolAgent 抽象基类。
    支持：describe、invoke、invoke_async、结构化返回与错误处理。
    """

    # ---------- MCP接口：工具元信息 ----------
    @abstractmethod
    def name(self) -> str:
        """工具唯一名称"""
        pass

    @abstractmethod
    def description(self) -> json:
        """工具功能说明（LLM 可读）"""
        pass

    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """输入参数 JSON Schema 格式"""
        pass

    @abstractmethod
    def output_schema(self) -> Optional[Dict[str, Any]]:
        """输出参数 JSON Schema，可选"""
        return None

    # ---------- 核心执行逻辑 ----------
    @abstractmethod
    def _run(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """同步核心逻辑，子类必须实现"""
        pass

    async def _arun(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """异步逻辑：默认包装同步逻辑，可被子类覆盖"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, inputs)

    # ---------- MCP标准接口：描述 ----------
    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.name(),
            "description": self.description(),
            "parameters": self.input_schema(),
            "returns": self.output_schema() or {
                "type": "object",
                "properties": {
                    "content": {"type": "array"},
                    "isError": {"type": "boolean"}
                }
            }
        }

    def supports_async(self) -> bool:
        return self._arun.__func__ != StrategyExecAgent._arun

    # ---------- 调用统一入口 ----------
    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return self._safe_invoke(self._run, inputs)

    async def invoke_async(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return await self._safe_invoke_async(self._arun, inputs)

    # ---------- 安全执行（统一结构 + 错误处理） ----------
    def _safe_invoke(self, func, inputs) -> Dict[str, Any]:
        try:
            jsonschema.validate(instance=inputs, schema=self.input_schema())
            result = func(inputs)
            return self._format_success(result)
        except Exception as e:
            return self._format_error(e)

    async def _safe_invoke_async(self, func, inputs) -> Dict[str, Any]:
        try:
            jsonschema.validate(instance=inputs, schema=self.input_schema())
            result = await func(inputs)
            return self._format_success(result)
        except Exception as e:
            return self._format_error(e)

    # ---------- 输出格式标准化 ----------
    def _format_success(self, result: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        content = []
        if isinstance(result, str):
            content.append({"type": "text", "text": result})
        elif isinstance(result, dict):
            content.append({"type": "text", "text": json.dumps(result, ensure_ascii=False)})
        return {
            "isError": False,
            "content": content
        }

    def _format_error(self, e: Exception) -> Dict[str, Any]:
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": f"工具执行出错：{str(e)}"
                }
            ]
        }
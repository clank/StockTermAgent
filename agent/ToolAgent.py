import inspect
from abc import ABC
from typing import Dict, Any, List


def mcp(name: str = None,
        useage: str = None,
        purpose: str = None,
        features: List[str] = None):
    """MCP协议Agent类装饰器"""

    def decorator(cls):
        if name is not None:
            cls.name = lambda self: name
        if useage is not None:
            cls.useage = lambda self: useage
        if purpose is not None:
            cls.purpose = lambda self: purpose
        if features is not None:
            cls.features = lambda self: features
        return cls

    return decorator


def tool_call(description: str = "",
              input_context: Dict[str, Any] = None,
              output_context: Dict[str, Any] = None):
    """工具调用方法装饰器"""

    def decorator(func):
        func.tool_description = description
        func.input_schema = input_context or {}
        func.output_schema = output_context or {}
        return func

    return decorator


class ToolAgent(ABC):
    """符合MCP协议的Agent抽象基类"""


    @property
    def name(self) -> str:
        """Agent唯一标识名称"""
        if hasattr(self, '_name'):
            return self._name
        return self.__class__.__name__  # 默认返回类名


    @property
    def purpose(self) -> str:
        """用途列表"""
        if self.purpose is not None:
            return self.purpose
        return "Generic ToolAgent purpose"

    @property
    def features(self) -> List[str]:
        """特性列表"""
        if self.features is not None:
            return self.features
        return ["Generic ToolAgent features"]

    @property
    def useage(self) -> str:
        """使用说明"""
        if self.useage is not None:
            return self.useage
        return "This is a generic ToolAgent."

    @property
    def profile_card(self) -> Dict[str, Any]:
        """Agent名片信息"""
        return {
            "name": self.name,
            "useage": self.usage,
            "purpose": self.purpose,
            "features": self.features,
            "tools": self.tool_call_behavior

        }

    @property
    def tool_call_behavior(self) -> Dict[str, Dict[str, Any]]:
        """获取所有带有tool_call注解的方法及其属性"""
        methods = {}

        for name, method in inspect.getmembers(self.__class__, inspect.isfunction):
            if hasattr(method, 'tool_description'):
                methods[name] = {
                    'description': getattr(method, 'tool_description', ''),
                    'input_schema': getattr(method, 'input_schema', {}),
                    'output_schema': getattr(method, 'output_schema', {})
                }

        return methods






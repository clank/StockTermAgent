from typing import Dict, Any, List, Callable, Optional
from abc import ABC
import inspect

def mcp(
    name: Optional[str] = None,
    usage: Optional[str] = None,
    purpose: Optional[str] = None,
    features: Optional[List[str]] = None,
) -> Callable:
    """MCP协议Agent类装饰器。

    该装饰器允许你为ToolAgent类定义元数据，
    使其更易于发现，并提供关于其功能的重要信息。

    参数:
        name: Agent的唯一标识符。默认为类名。
        usage: Agent的使用说明。
        purpose: Agent的主要目标或功能。
        features: Agent的关键能力或属性列表。

    返回:
        一个用于修饰类的装饰器函数。
    """

    def decorator(cls: type) -> type:
        """实际用于修饰类的装饰器函数。"""
        orig_init = cls.__init__
        def __init__(self, *args, **kwargs):
            if name is not None:
                self._name = name
            if usage is not None:
                self._usage = usage
            if purpose is not None:
                self._purpose = purpose
            if features is not None:
                self._features = features
            orig_init(self, *args, **kwargs)
        cls.__init__ = __init__
        return cls

    return decorator


def tool_call(
    description: str = "",
    input_context: Optional[Dict[str, Any]] = None,
    output_context: Optional[Dict[str, Any]] = None,
) -> Callable:
    """用于标记方法为可工具调用的装饰器。

    该装饰器为方法添加元数据，表明它可以被Agent作为工具调用。
    同时定义了工具的输入和输出schema。

    参数:
        description: 对工具功能的人类可读描述。
        input_context: 工具输入的schema定义字典。
        output_context: 工具输出的schema定义字典。

    返回:
        一个用于修饰方法的装饰器函数。
    """

    def decorator(func: Callable) -> Callable:
        """实际用于修饰方法的装饰器函数。"""
        func.tool_description = description
        func.input_context = input_context or {}
        func.output_context = output_context or {}
        return func

    return decorator


class ToolAgent(ABC):
    """符合MCP协议的Agent抽象基类。

    该类为创建符合MCP协议的Agent提供基础。
    定义了所有ToolAgent应具备的核心属性和方法。
    """

    # 使用Optional[str]和Optional[List[str]]表示这些属性可以为None
    _name: Optional[str] = None
    _purpose: Optional[str] = None
    _usage: Optional[str] = None
    _features: Optional[List[str]] = None

    @property
    def name(self) -> str:
        """Agent的唯一标识符。

        如果未显式设置，则默认为类名。
        """
        return self._name if self._name else self.__class__.__name__

    @property
    def purpose(self) -> str:
        """Agent的用途。"""
        return self._purpose if self._purpose else "Generic ToolAgent purpose"

    @property
    def features(self) -> List[str]:
        """Agent的特性列表。"""
        return self._features if self._features else ["Generic ToolAgent features"]

    @property
    def usage(self) -> str:
        """Agent的使用说明。"""
        return self._usage if self._usage else "This is a generic ToolAgent usage"

    @property
    def profile_card(self) -> Dict[str, Any]:
        """Agent的名片信息。"""
        return {
            "name": self.name,
            "usage": self.usage,
            "purpose": self.purpose,
            "features": self.features,
            "tools": self.tool_call_behavior,
        }

    @property
    def tool_call_behavior(self) -> Dict[str, Dict[str, Any]]:
        """获取所有被@tool_call装饰的方法及其属性。

        该属性动态检查类，查找被tool_call装饰的方法，并提取相关数据（description、input_context、output_context）。
        """
        methods = {}
        for name, method in inspect.getmembers(self.__class__, inspect.isfunction):
            if hasattr(method, "tool_description"):
                methods[name] = {
                    "description": getattr(method, "tool_description", ""),
                    "input_context": getattr(method, "input_context", {}),
                    "output_context": getattr(method, "output_context", {}),
                }
        return methods
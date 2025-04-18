import inspect
from abc import ABC
from typing import Dict, Any, List, Callable, Optional


def mcp(
    name: Optional[str] = None,
    usage: Optional[str] = None,
    purpose: Optional[str] = None,
    features: Optional[List[str]] = None,
) -> Callable:
    """MCP protocol Agent class decorator.

    This decorator allows you to define metadata for your ToolAgent classes,
    making them more discoverable and providing essential information
    about their functionality.

    Args:
        name: The unique identifier for the agent. Defaults to the class name.
        usage: A description of how the agent should be used.
        purpose:  The primary goal or function of the agent.
        features: A list of key capabilities or attributes of the agent.

    Returns:
        A decorator function that modifies the class.
    """

    def decorator(cls: type) -> type:
        """The actual decorator function that modifies the class."""
        if name:
            cls.name = lambda self: name  # type: ignore  # See note below
        if usage:
            cls.usage = lambda self: usage  # type: ignore
        if purpose:
            cls.purpose = lambda self: purpose  # type: ignore
        if features:
            cls.features = lambda self: features  # type: ignore
        return cls

    return decorator


def tool_call(
    description: str = "",
    input_context: Optional[Dict[str, Any]] = None,
    output_context: Optional[Dict[str, Any]] = None,
) -> Callable:
    """Decorator for marking methods as tool-callable.

    This decorator adds metadata to a method, indicating that it can be
    invoked as a tool by an agent.  It also defines the input and
    output schemas for the tool.

    Args:
        description: A human-readable description of what the tool does.
        input_context:  A dictionary defining the schema for the tool's input.
        output_context: A dictionary defining the schema for the tool's output.

    Returns:
        A decorator function that modifies the method.
    """

    def decorator(func: Callable) -> Callable:
        """The actual decorator."""
        func.tool_description = description
        func.input_schema = input_context or {}
        func.output_schema = output_context or {}
        return func

    return decorator


class ToolAgent(ABC):
    """Abstract base class for MCP-compliant agents.

    This class provides a foundation for creating agents that adhere to
    the MCP protocol.  It defines the core attributes and methods
    that all ToolAgents should possess.
    """

    #  Use Optional[str] and Optional[List[str]] to indicate that these can be None
    _name: Optional[str] = None
    _purpose: Optional[str] = None
    _usage: Optional[str] = None
    _features: Optional[List[str]] = None

    @property
    def name(self) -> str:
        """Unique identifier for the agent.

        Defaults to the class name if not explicitly set.
        """
        return self._name if self._name else self.__class__.__name__

    @property
    def purpose(self) -> str:
        """The purpose of the agent."""
        return self._purpose if self._purpose else "Generic ToolAgent purpose"

    @property
    def features(self) -> List[str]:
        """List of agent features."""
        return self._features if self._features else ["Generic ToolAgent features"]

    @property
    def usage(self) -> str:
        """Usage instructions for the agent."""
        return self._usage if self._usage else "This is a generic ToolAgent."

    @property
    def profile_card(self) -> Dict[str, Any]:
        """Agent's profile information."""
        return {
            "name": self.name,
            "usage": self.usage,
            "purpose": self.purpose,
            "features": self.features,
            "tools": self.tool_call_behavior,
        }

    @property
    def tool_call_behavior(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves methods decorated with @tool_call and their attributes.

        This property dynamically inspects the class to find methods
        decorated with the `tool_call` decorator and extracts the
        associated metadata (description, input schema, and output schema).
        """
        methods = {}
        for name, method in inspect.getmembers(self.__class__, inspect.isfunction):
            if hasattr(method, "tool_description"):
                methods[name] = {
                    "description": getattr(method, "tool_description", ""),
                    "input_schema": getattr(method, "input_schema", {}),
                    "output_schema": getattr(method, "output_schema", {}),
                }
        return methods

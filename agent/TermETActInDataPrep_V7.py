from typing import Dict, Any, Union, Optional
import json


from StrategyExecAgent import StrategyExecAgent


class TermETActInDataPreper(StrategyExecAgent) :
    def name(self) -> str:
        return "TermETActInDataPreper"

    def description(self) -> json:
        desc = {
            "name": "TermETActInDataPreper",
            "parent_class": "StrategyExecAgent",
            "protocol": "MCP",
            "function": "将 epub 文档转换为 markdown 格式文档",
            "input": {
                "schema": "由 input_schema 方法定义",
                "description": "执行转换操作所需的输入数据，需符合指定模式"
            },
            "output": {
                "schema": "由 output_schema 方法定义",
                "description": "转换操作完成后输出的数据，遵循指定模式"
            },
            "implementation": {
                "method": "_run",
                "description": "具体的 epub 转 markdown 实现逻辑所在方法"
            }
        }
        return desc


    def input_schema(self) -> Dict[str, Any]:
        pass

    def output_schema(self) -> Optional[Dict[str, Any]]:
        pass

    def _run(self, inputs: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        pass
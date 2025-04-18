import sys
sys.path.append('/Users/alsc/PycharmProjects')

from fastapi import FastAPI
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from StockTermAgent.tool.EpubToMDConverter_V6 import EpubToMDConverter, ConversionType


app = FastAPI()
mcp = FastMCP()

# 存储工具代理的字典
tool_agents: Dict[str, Any] = {}

# 注册工具函数
@mcp.tool()
def create_markdown_files():
    """将 epub 文件转换为 markdown 文档，支持多种输出模式"""
    converter = EpubToMDConverter("file/日本蜡烛图技术epub.epub")
    # 转换为多个文件
    converter.convert(ConversionType.MULTIPLE_FILES, "file/技术分析")

# 初始化工具代理
@app.on_event("startup")
async def startup_event():
    # 这里可以添加更多工具代理的初始化逻辑
    tool_agents['create_markdown_files'] = create_markdown_files

# 获取所有工具代理
@app.get("/tool_agents")
def get_tool_agents():
    return list(tool_agents.keys())

# 根据名称获取工具代理
@app.get("/tool_agents/{tool_name}")
def get_tool_agent(tool_name: str):
    if tool_name in tool_agents:
        return {"tool_name": tool_name, "status": "available"}
    else:
        return {"tool_name": tool_name, "status": "not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
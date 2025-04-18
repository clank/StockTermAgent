import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP()  # 初始化 MCP 服务实例

@mcp.tool()
def get_desktop_files():
    """获取桌面上的文件列表"""
    return os.listdir(os.path.expanduser("file"))

if __name__ == "__main__":
    mcp.run(transport='stdio')  # 启动服务，使用标准输入输出通信
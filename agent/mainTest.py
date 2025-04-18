from mcp.server.fastmcp import FastMCP
import sys


sys.path.append('/Users/alsc/PycharmProjects')

from StockTermAgent.tool.EpubToMDConverter_V6 import EpubToMDConverter, ConversionType

mcp = FastMCP()  # 初始化 MCP 服务实例


@mcp.tool()
def create_markdown_files():
    """将epub文件转换为markdown文档，支持多种输出模式"""

    converter = EpubToMDConverter("file/日本蜡烛图技术epub.epub")
    # 转换为多个文件
    converter.convert(ConversionType.MULTIPLE_FILES, "file/技术分析")





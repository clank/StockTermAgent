from typing import Dict, Any
from .ToolAgent_V3 import ToolAgent, mcp, tool_call
from ..tool.EpubToMDConverter_V6 import EpubToMDConverter, ConversionType

@mcp(
    name="Epub2MarkDownAgent",
    usage="将epub电子书批量或单本转换为markdown文档",
    purpose="实现epub到markdown的自动化转换，支持多种输出格式",
    features=["epub转markdown", "支持多种输出格式", "自动提取图片", "支持多文件/单文件/内嵌图片"]
)
class Epub2MarkDownAgent(ToolAgent):
    @tool_call(
        description="将epub文件转换为markdown文档，支持多种输出模式",
        input_context={
            "epub_path": "epub文件路径（str）",
            "output_path": "输出markdown路径（str）",
            "conversion_type": "转换类型（str，可选：multiple_files, single_file, single_file_with_base64）"
        },
        output_context={
            "success": "转换是否成功（bool）",
            "message": "转换结果信息（str）"
        }
    )
    def run(self, epub_path: str, output_path: str, conversion_type: str = "single_file") -> Dict[str, Any]:
        try:
            converter = EpubToMDConverter(epub_path)
            # 转换类型映射
            type_map = {
                "multiple_files": ConversionType.MULTIPLE_FILES,
                "single_file": ConversionType.SINGLE_FILE,
                "single_file_with_base64": ConversionType.SINGLE_FILE_WITH_BASE64
            }
            conv_type = type_map.get(conversion_type, ConversionType.SINGLE_FILE)
            converter.convert(conv_type, output_path)
            return {
                "success": True,
                "message": f"转换成功，输出路径：{output_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"转换失败: {str(e)}"
            }
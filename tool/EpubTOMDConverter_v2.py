import os
from pathlib import Path
import logging
import argparse
import yaml
from wisup_e2m import E2MParser, E2MConverter
from pathlib import Path


# ===== 日志配置 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s - [%(funcName)s - %(module)s]",
    handlers=[
        logging.StreamHandler(),  # 打印到控制台
        logging.FileHandler("epub_conversion.log", mode='a', encoding="utf-8")  # 输出到文件
    ]
)

# 配置日志对象
logger = logging.getLogger()


# ===== 配置加载 =====
def load_config(config_path):
    try:
        logger.debug("🔧 正在加载配置文件...")
        yaml_config_path = Path(config_path)
        with open(yaml_config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
        logger.info("✅ 配置文件加载成功")
        return config
    except Exception as e:
        logger.error(f"❌ 无法加载配置文件 {config_path}: {str(e)}")
        raise


# ===== EPUB 转换逻辑 =====
def convert_epub_to_markdown(input_file, output_dir, config):
    # 获取输出文件名和图像目录
    epub_input_file=Path(input_file)
    output_md = os.path.join(output_dir, f"{epub_input_file.stem}.md")
    image_folder = os.path.join(output_dir, "images")

    # 确保输出目录和图像目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(image_folder).mkdir(parents=True, exist_ok=True)

    logger.info(f"📘 开始解析 EPUB 文件：{input_file}")

    # 初始化解析器和转换器
    parser = E2MParser.from_config(config)
    converter = E2MConverter.from_config(config)

    try:
        logger.debug(f"🔍 正在解析 EPUB 文件内容...")
        parsed = parser.parse(file_name=str(epub_input_file))

        logger.debug(f"🔄 正在转换为 Markdown 格式...")
        markdown_text = converter.convert(text=parsed.text, images=parsed.images)

        # 将转换结果写入文件
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        logger.info(f"✅ 成功生成 Markdown 文件：{output_md}")
        return output_md
    except Exception as e:
        logger.error(f"❌ 处理 EPUB 文件时发生错误：{str(e)}")
        raise


# ===== 命令行参数 =====
def parse_args():
    parser = argparse.ArgumentParser(description="EPUB 转 Markdown")
    parser.add_argument("--input", type=str, required=True, help="输入的 EPUB 文件路径")
    parser.add_argument("--output", type=str, required=True, help="输出的目录路径")
    parser.add_argument("--config", type=str, required=True, help="配置文件路径")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    return parser.parse_args()


if __name__ == "__main__":
    # 处理命令行参数
    args = parse_args()



    # 启用调试模式
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("🔧 调试模式已启用")

    try:
        # 加载配置文件
        config = load_config(args.config)

        # 执行转换操作
        convert_epub_to_markdown(args.input, args.output, config)

    except Exception as e:
        logger.critical(f"❌ 程序执行失败: {str(e)}")
        exit(1)
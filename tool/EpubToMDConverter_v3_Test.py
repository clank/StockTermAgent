from EpubToMDConverter_V5 import EpubToMDConverter


def main():
    try:
        # 使用示例
        epub_path = "file/市场技术分析.epub"
        reader = EpubToMDConverter(epub_path)

        # 分析epub内容
        reader.analyze()

        # 转换为单个Markdown文件（包含图片）
        reader.save_as_single_file_markdown()

        # 转换为多个Markdown文件
        reader.save_as_markdown(output_dir='file/市场技术分析')

    except Exception as e:
        print(f"Error processing epub file: {str(e)}")


if __name__ == "__main__":
    main()
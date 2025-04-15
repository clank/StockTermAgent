import os
import shutil
import argparse
import pathlib
import subprocess
import logging
from bs4 import BeautifulSoup
from ebooklib import epub

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def extract_epub(epub_path, output_dir):
    book = epub.read_epub(epub_path)
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    chapters = []
    image_count = 0

    for item in book.get_items():
        try:
            # ✅ 图像识别方式：通过 media_type 判断
            if item.media_type.startswith("image/"):
                image_ext = item.media_type.split("/")[-1]
                image_path = images_dir / f"image_{image_count:04d}.{image_ext}"
                with open(image_path, "wb") as f:
                    f.write(item.get_content())
                image_count += 1
                logger.debug(f"✅ 提取图片: {image_path}")

            # ✅ 文档识别方式：HTML/XHTML 内容
            elif item.media_type in ["application/xhtml+xml", "text/html"]:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                title_tag = soup.find(['h1', 'h2', 'h3'])
                title = title_tag.get_text(strip=True).replace(" ", "_") if title_tag else f"chapter_{len(chapters)+1}"
                filename = f"{len(chapters)+1:02d}_{title}.html"
                filepath = output_dir / filename

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(str(soup))
                chapters.append(filepath)
                logger.debug(f"✅ 提取章节: {filepath}")

        except Exception as e:
            logger.error(f"❌ 错误：{e}")

    logger.info(f"✅ 提取完成：{len(chapters)} 章，{image_count} 张图片")
    return chapters, images_dir


def convert_html_to_md(html_file, md_file):
    subprocess.run([
        "pandoc",
        "-f", "html",
        "-t", "markdown",
        "-o", str(md_file),
        str(html_file)
    ], check=True)


def batch_convert_to_markdown(chapter_files, output_dir):
    md_dir = output_dir / "markdown"
    md_dir.mkdir(exist_ok=True)

    for html_file in chapter_files:
        md_filename = html_file.stem + ".md"
        md_path = md_dir / md_filename
        convert_html_to_md(html_file, md_path)

    print(f"📄 所有章节已转换为 Markdown，路径：{md_dir}")
    return md_dir


def clean_html_dir(output_dir):
    for file in pathlib.Path(output_dir).glob("*.html"):
        file.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epub", required=True, help="EPUB 文件路径")
    parser.add_argument("--output", required=True, help="输出目录")
    args = parser.parse_args()

    epub_path = args.epub
    output_dir = pathlib.Path(args.output)

    print(f"📘 正在处理 EPUB：{epub_path}")
    chapters, _ = extract_epub(epub_path, output_dir)
    batch_convert_to_markdown(chapters, output_dir)
    clean_html_dir(output_dir)


if __name__ == "__main__":
    main()

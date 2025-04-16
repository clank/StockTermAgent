import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import html2text
import os
import base64
import re
from tqdm import tqdm
from urllib.parse import unquote
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('epub_converter.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# 定义常量
METADATA_FIELDS = {
    'title': ('DC', 'title'),
    'creator': ('DC', 'creator'),
    'language': ('DC', 'language'),
    'publisher': ('DC', 'publisher'),
    'identifier': ('DC', 'identifier'),
    'date': ('DC', 'date'),
    'description': ('DC', 'description'),
    'rights': ('DC', 'rights'),
    'subject': ('DC', 'subject')
}

IMAGE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/svg+xml': '.svg'
}


class EpubToMDConverter:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.book = None
        self.metadata = {}
        self.images = {}
        self.html2text = self._init_html_converter()

    def _init_html_converter(self):
        """初始化 HTML 转 Markdown 转换器"""
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0
        converter.unicode_snob = True
        converter.skip_internal_links = True
        return converter

    def load_book(self):
        try:
            self.book = epub.read_epub(self.epub_path)
            logger.info(f"成功加载epub文件: {self.epub_path}")
            return True
        except Exception as e:
            logger.error(f"加载epub文件失败: {str(e)}")
            return False

    def get_metadata(self):
        if not self.book:
            logger.warning("书籍未加载，无法获取元数据")
            return

        for field, (namespace, name) in METADATA_FIELDS.items():
            value = self.book.get_metadata(namespace, name)
            self.metadata[field] = self._get_metadata_value(value)
        logger.info("成功获取书籍元数据")

    def _get_metadata_value(self, value):
        """获取元数据的值"""
        if value and value[0]:
            return value[0][0] if isinstance(value[0], tuple) else value[0]
        return "未知"

    def print_metadata(self):
        logger.info("打印书籍元数据")
        print("\n书籍元数据:")
        print("-" * 50)
        for key, value in self.metadata.items():
            print(f"{key.capitalize()}: {value}")

    def print_toc(self, toc=None, level=0):
        """改进的目录打印函数"""
        if toc is None:
            toc = self.book.toc
            logger.info("打印目录结构")
            print("\n目录结构:")
            print("-" * 50)
            if not toc:
                logger.warning("没有找到目录结构")
                print("没有找到目录结构")
                return

        for item in toc:
            try:
                if isinstance(item, tuple):
                    title = item[0] if len(item) > 0 else "未知标题"
                    children = item[2] if len(item) > 2 else []
                    print("  " * level + f"- {title}")
                    if children:
                        self.print_toc(children, level + 1)
                elif isinstance(item, list):
                    self.print_toc(item, level)
                else:
                    print("  " * level + f"- {str(item)}")
            except Exception as e:
                logger.error(f"处理目录项时出错: {str(e)}")
                print(f"处理目录项时出错: {str(e)}")
                continue

    def get_chapter_content(self, chapter):
        try:
            soup = BeautifulSoup(chapter.get_content(), 'html.parser')
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            return h.handle(str(soup))
        except Exception as e:
            logger.error(f"解析章节内容时出错: {str(e)}")
            return f"解析章节内容时出错: {str(e)}"

    def print_chapters(self, max_preview_length=200):
        logger.info("打印章节内容")
        print("\n章节内容:")
        print("-" * 50)

        chapters_found = False
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters_found = True
                print(f"\n文档ID: {item.id}")
                content = self.get_chapter_content(item)
                preview = content[:max_preview_length]
                if len(content) > max_preview_length:
                    preview += "..."
                print(preview + "\n")
                print("-" * 50)

        if not chapters_found:
            logger.warning("没有找到章节内容")
            print("没有找到章节内容")

    def analyze(self):
        if not self.load_book():
            logger.error("加载书籍失败，无法进行分析")
            return

        try:
            self.get_metadata()
            self.print_metadata()
            self.print_toc()
            self.print_chapters()
            logger.info("书籍分析完成")
        except Exception as e:
            logger.error(f"分析过程中出错: {str(e)}")
            print(f"分析过程中出错: {str(e)}")

    def _clean_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        return re.sub(r'[\\/*?:"<>|]', '', filename)

    def _get_chapter_markdown(self, chapter) -> str:
        """将章节内容转换为Markdown格式"""
        try:
            soup = BeautifulSoup(chapter.get_content(), 'html.parser')
            title = self._get_chapter_title(soup)
            markdown = self.html2text.handle(str(soup))
            if title and not markdown.startswith(f"# {title}"):
                markdown = f"# {title}\n\n{markdown}"
            return markdown
        except Exception as e:
            logger.error(f"转换章节内容时出错: {str(e)}")
            return f"转换章节内容时出错: {str(e)}"

    def _get_chapter_title(self, soup):
        """获取章节标题"""
        h1 = soup.find('h1')
        return h1.get_text().strip() if h1 else ""

    def _extract_images(self):
        """提取epub中的所有图片"""
        logger.info("开始提取epub中的所有图片")
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                image_id = item.id
                image_content = item.content
                image_name = unquote(item.file_name.split('/')[-1])
                self.images[image_id] = {
                    'content': image_content,
                    'name': image_name,
                    'media_type': item.media_type
                }
        logger.info(f"成功提取 {len(self.images)} 张图片")

    def _save_images(self, output_dir: str) -> dict:
        """保存图片到assets目录"""
        logger.info(f"开始保存图片到 {output_dir}/assets 目录")
        assets_dir = self._create_directory(output_dir, 'assets')
        image_paths = {}
        for image_id, image_data in self.images.items():
            safe_name = self._get_safe_image_name(image_data)
            image_path = os.path.join(assets_dir, safe_name)
            image_name = safe_name.split('/')[-1].split('.')[0]
            try:
                self._write_file(image_path, image_data['content'])
                image_paths[image_name] = os.path.join('assets', safe_name)
            except Exception as e:
                logger.error(f"保存图片 {image_id} 失败: {str(e)}")
        logger.info(f"成功保存 {len(image_paths)} 张图片")
        return image_paths

    def _create_directory(self, base_dir, sub_dir):
        """创建目录"""
        path = os.path.join(base_dir, sub_dir)
        os.makedirs(path, exist_ok=True)
        return path

    def _get_safe_image_name(self, image_data):
        """获取安全的图片文件名"""
        safe_name = self._clean_filename(image_data['name'])
        if not safe_name:
            safe_name = f"image_{id(image_data)}{self._get_extension(image_data['media_type'])}"
        return safe_name

    def _get_extension(self, media_type: str) -> str:
        """根据媒体类型获取文件扩展名"""
        return IMAGE_EXTENSIONS.get(media_type, '.jpg')

    def _write_file(self, path, content):
        """写入文件"""
        with open(path, 'wb') as f:
            f.write(content)

    def _process_html_content(self, html_content: str, image_paths: dict) -> str:
        """处理HTML内容，替换图片引用"""
        logger.info("开始处理HTML内容，替换图片引用")
        soup = BeautifulSoup(html_content, 'html.parser')
        for img in soup.find_all('img'):
            src = img.get('src', '')
            image_name = src.split('/')[-1].split('.')[0]
            if image_name in image_paths:
                img['src'] = image_paths[image_name]
                if not img.get('alt'):
                    img['alt'] = f"Image {image_name}"
        logger.info("HTML内容处理完成")
        return str(soup)

    def _write_metadata_to_file(self, file_path, book_title):
        """将元数据写入文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {book_title}\n\n")
                f.write("## 图书信息\n\n")
                for key, value in self.metadata.items():
                    f.write(f"- **{key.capitalize()}**: {value}\n")
                f.write("\n## 目录\n\n")
            logger.info(f"成功创建文件: {file_path}")
        except Exception as e:
            logger.error(f"创建文件失败: {str(e)}")

    def save_as_markdown(self, output_dir: str = None) -> None:
        """将epub内容保存为Markdown文件"""
        if not self._ensure_book_loaded():
            return

        self.get_metadata()
        self._extract_images()
        book_title = self._clean_filename(self.metadata.get('title', 'unknown_book'))
        output_dir = output_dir or f"{book_title}_markdown"
        self._create_directory("", output_dir)
        image_paths = self._save_images(output_dir)
        readme_path = os.path.join(output_dir, "README.md")
        self._write_metadata_to_file(readme_path, book_title)

        logger.info("开始转换章节...")
        chapter_index = 1
        for item in tqdm(self.book.get_items()):
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                try:
                    processed_html = self._process_html_content(item.get_content().decode('utf-8'), image_paths)
                    markdown_content = self.html2text.handle(processed_html)
                    chapter_filename = f"chapter_{chapter_index:03d}.md"
                    chapter_path = os.path.join(output_dir, chapter_filename)
                    self._write_file(chapter_path, markdown_content.encode('utf-8'))
                    self._update_readme(readme_path, markdown_content, chapter_filename, chapter_index)
                    chapter_index += 1
                except Exception as e:
                    logger.error(f"保存章节 {chapter_index} 失败: {str(e)}")

        self._print_conversion_summary(output_dir, chapter_index - 1, len(image_paths), readme_path)

    def _ensure_book_loaded(self):
        """确保书籍已加载"""
        if not self.book:
            if not self.load_book():
                logger.error("加载书籍失败，操作终止")
                return False
        return True

    def _update_readme(self, readme_path, markdown_content, chapter_filename, chapter_index):
        """更新 README 文件"""
        try:
            title = markdown_content.split('\n', 1)[0].lstrip("#").strip()
            if not title:
                title = f"Chapter {chapter_index}"
            with open(readme_path, "a", encoding="utf-8") as f:
                f.write(f"- [{title}]({chapter_filename})\n")
        except Exception as e:
            logger.error(f"更新 README 文件失败: {str(e)}")

    def _print_conversion_summary(self, output_dir, chapter_count, image_count, readme_path):
        """打印转换总结信息"""
        logger.info(f"\n转换完成！")
        logger.info(f"- 文件保存在: {output_dir}")
        logger.info(f"- 总计转换 {chapter_count} 个章节")
        logger.info(f"- 总计处理 {image_count} 张图片")
        logger.info(f"- 目录索引保存在: {readme_path}")
        print(f"\n转换完成！")
        print(f"- 文件保存在: {output_dir}")
        print(f"- 总计转换 {chapter_count} 个章节")
        print(f"- 总计处理 {image_count} 张图片")
        print(f"- 目录索引保存在: {readme_path}")

    def save_as_single_markdown(self, output_path: str = None) -> None:
        """将epub内容保存为单个Markdown文件"""
        if not self._ensure_book_loaded():
            return

        self.get_metadata()
        self._extract_images()
        book_title = self._clean_filename(self.metadata.get('title', 'unknown_book'))
        output_path = output_path or f"{book_title}.md"
        output_dir = os.path.dirname(output_path) or '.'
        image_paths = self._save_images(output_dir)

        logger.info(f"\n开始转换为单个Markdown文件...")
        print(f"\n开始转换为单个Markdown文件...")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_metadata_to_file(output_path, book_title)
                f.write("\n---\n\n")

                chapter_count = 0
                for item in tqdm(self.book.get_items()):
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        try:
                            processed_html = self._process_html_content(item.get_content().decode('utf-8'), image_paths)
                            markdown_content = self.html2text.handle(processed_html)
                            f.write(f"\n{markdown_content}\n")
                            f.write("\n---\n\n")
                            chapter_count += 1
                        except Exception as e:
                            logger.error(f"处理章节 {chapter_count + 1} 失败: {str(e)}")

            self._print_conversion_summary(output_path, chapter_count, len(image_paths), output_path)
        except Exception as e:
            logger.error(f"保存单个Markdown文件失败: {str(e)}")

    def save_as_single_file_markdown(self, output_path: str = None) -> None:
        """将epub内容（包括图片）保存为单个独立的Markdown文件"""
        if not self._ensure_book_loaded():
            return

        self.get_metadata()
        self._extract_images()
        book_title = self._clean_filename(self.metadata.get('title', 'unknown_book'))
        output_path = output_path or f"{book_title}_single.md"
        image_data = self._encode_images_to_base64()

        logger.info(f"\n开始转换为单个独立Markdown文件...")
        print(f"\n开始转换为单个独立Markdown文件...")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                self._write_metadata_to_file(output_path, book_title)
                f.write("\n---\n\n")

                chapter_count = 0
                for item in tqdm(self.book.get_items()):
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        try:
                            soup = BeautifulSoup(item.get_content().decode('utf-8'), 'html.parser')
                            self._replace_images_with_base64(soup, image_data)
                            markdown_content = self.html2text.handle(str(soup))
                            f.write(f"\n{markdown_content}\n")
                            f.write("\n---\n\n")
                            chapter_count += 1
                        except Exception as e:
                            logger.error(f"处理章节 {chapter_count + 1} 失败: {str(e)}")

            self._print_conversion_summary(output_path, chapter_count, len(image_data), output_path)
        except Exception as e:
            logger.error(f"保存单个独立Markdown文件失败: {str(e)}")

    def _encode_images_to_base64(self):
        """将图片编码为 base64 数据"""
        image_data = {}
        for image_id, img in self.images.items():
            try:
                b64_data = base64.b64encode(img['content']).decode()
                image_data[image_id] = f"data:{img['media_type']};base64,{b64_data}"
            except Exception as e:
                logger.error(f"处理图片 {image_id} 为base64数据失败: {str(e)}")
        return image_data

    def _replace_images_with_base64(self, soup, image_data):
        """将 HTML 中的图片引用替换为 base64 数据"""
        for img in soup.find_all('img'):
            src = img.get('src', '')
            image_id = src.split('/')[-1].split('.')[0]
            if image_id in image_data:
                img['src'] = image_data[image_id]
                if not img.get('alt'):
                    img['alt'] = f"Image {image_id}"
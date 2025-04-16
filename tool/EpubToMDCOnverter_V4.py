import os
import re
import base64
from urllib.parse import unquote
from ebooklib import epub
from bs4 import BeautifulSoup
import html2text


class EpubReader:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.book = None
        self.metadata = {}
        self.images = {}  # key: image filename, value: {content, media_type}
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0
        self.html2text.unicode_snob = True
        self.html2text.skip_internal_links = True

    def _clean_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', '', name)

    def _get_extension(self, media_type: str) -> str:
        return {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/svg+xml': '.svg'
        }.get(media_type, '.jpg')

    def load_book(self):
        self.book = epub.read_epub(self.epub_path)

    def extract_metadata(self):
        fields = {
            'title': ('DC', 'title'),
            'creator': ('DC', 'creator'),
            'language': ('DC', 'language'),
            'publisher': ('DC', 'publisher'),
        }
        for key, (ns, name) in fields.items():
            value = self.book.get_metadata(ns, name)
            self.metadata[key] = value[0][0] if value else "未知"

    def extract_images(self):
        for item in self.book.get_items():
            if item.get_type() == epub.ITEM_IMAGE:
                filename = unquote(os.path.basename(item.file_name))
                self.images[filename] = {
                    'content': item.content,
                    'media_type': item.media_type
                }

    def save_images(self, output_dir: str) -> dict:
        assets_dir = os.path.join(output_dir, 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        image_paths = {}

        for filename, data in self.images.items():
            safe_name = self._clean_filename(filename)
            path = os.path.join(assets_dir, safe_name)
            with open(path, 'wb') as f:
                f.write(data['content'])
            image_paths[filename] = os.path.join('assets', safe_name)
        return image_paths

    def process_html_content(self, html: str, image_paths: dict) -> str:
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            src = img.get('src', '')
            filename = unquote(os.path.basename(src))
            if filename in image_paths:
                img['src'] = image_paths[filename]
                if not img.get('alt'):
                    img['alt'] = filename
        return str(soup)

    def convert_to_markdown_files(self, output_dir: str):
        self.load_book()
        self.extract_metadata()
        self.extract_images()
        image_paths = self.save_images(output_dir)

        title = self._clean_filename(self.metadata.get('title', 'book'))
        os.makedirs(output_dir, exist_ok=True)
        readme = os.path.join(output_dir, "README.md")

        with open(readme, "w", encoding="utf-8") as index:
            index.write(f"# {title}\n\n")
            index.write("## 图书信息\n\n")
            for key, value in self.metadata.items():
                index.write(f"- **{key.capitalize()}**: {value}\n")
            index.write("\n## 目录\n\n")

        count = 1
        for item in self.book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                html = item.get_content().decode("utf-8")
                html = self.process_html_content(html, image_paths)
                markdown = self.html2text.handle(html)
                chapter_file = f"chapter_{count:03}.md"
                chapter_path = os.path.join(output_dir, chapter_file)

                with open(chapter_path, "w", encoding="utf-8") as f:
                    f.write(markdown)

                # 目录索引更新
                title_line = markdown.split("\n", 1)[0].strip("#").strip()
                if not title_line:
                    title_line = f"Chapter {count}"
                with open(readme, "a", encoding="utf-8") as index:
                    index.write(f"- [{title_line}]({chapter_file})\n")

                count += 1

        print(f"\n转换完成！")
        print(f"- 输出目录：{output_dir}")
        print(f"- 转换章节数：{count - 1}")
        print(f"- 图片数量：{len(image_paths)}")
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
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any, List, Tuple
from abc import ABC, abstractmethod

# ============= 配置模块 =============
@dataclass
class ConverterConfig:
    """转换器配置"""
    output_dir: str
    image_quality: int = 85
    max_image_size: int = 1024 * 1024
    chunk_size: int = 1024 * 1024
    assets:str='assets'

class ConversionType(Enum):
    """转换类型"""
    MULTIPLE_FILES = "multiple_files"
    SINGLE_FILE = "single_file"
    SINGLE_FILE_WITH_BASE64 = "single_file_with_base64"

# 常量定义
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

# ============= 日志模块 =============
def setup_logger():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('epub_converter.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()

# ============= 异常模块 =============
class EpubConverterError(Exception):
    """基础异常类"""
    pass

class BookNotLoadedError(EpubConverterError):
    """书籍未加载异常"""
    pass

class MetadataExtractionError(EpubConverterError):
    """元数据提取异常"""
    pass

# ============= 工具模块 =============
class FileUtils:
    @staticmethod
    def clean_filename(filename: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', '', filename)

    @staticmethod
    def create_directory(base_dir: str, sub_dir: str) -> str:
        path = os.path.join(base_dir, sub_dir)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def write_file(path: str, content: bytes) -> None:
        with open(path, 'wb') as f:
            f.write(content)

# ============= 图片处理模块 =============
class ImageProcessor:
    @staticmethod
    def get_extension(media_type: str) -> str:
        return IMAGE_EXTENSIONS.get(media_type, '.jpg')

    @staticmethod
    def encode_to_base64(content: bytes, media_type: str) -> str:
        b64_data = base64.b64encode(content).decode()
        return f"data:{media_type};base64,{b64_data}"

# ============= HTML处理模块 =============
class HtmlProcessor:
    @staticmethod
    def init_html_converter() -> html2text.HTML2Text:
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0
        converter.unicode_snob = True
        converter.skip_internal_links = True
        return converter

    @staticmethod
    def get_chapter_title(soup: BeautifulSoup) -> str:
        h1 = soup.find('h1')
        return h1.get_text().strip() if h1 else ""

# ============= 主转换器类 =============
class EpubToMDConverter:
    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.book = None
        self.metadata = {}
        self.images = {}
        self.html2text = HtmlProcessor.init_html_converter()
        self.file_utils = FileUtils()
        self.image_processor = ImageProcessor()

    def _ensure_book_loaded(self) -> bool:
        """确保书籍已加载"""
        if not self.book:
            if not self.load_book():
                logger.error("预加载书籍失败，操作终止")
                return False
        try:
            self.get_metadata()
            self.print_metadata()
            self.print_toc()
            self.print_chapters()
            logger.info("书籍预加载完成")
        except Exception as e:
            logger.error(f"预加载过程中出错，操作继续: {str(e)}")
             
        return True
        

    

        

    def load_book(self) -> bool:
        """加载EPUB文件"""
        try:
            self.book = epub.read_epub(self.epub_path)
            logger.info(f"成功加载epub文件: {self.epub_path}")
            return True
        except Exception as e:
            logger.error(f"加载epub文件失败: {str(e)}")
            return False

    def _extract_metadata(self) -> None:
        """提取元数据"""
        if not self.book:
            raise BookNotLoadedError("书籍未加载，无法获取元数据")

        try:
            for field, (namespace, name) in METADATA_FIELDS.items():
                value = self.book.get_metadata(namespace, name)
                self.metadata[field] = value[0][0] if value and value[0] else "未知"
            logger.info("成功获取书籍元数据")
        except Exception as e:
            raise MetadataExtractionError(f"提取元数据失败: {str(e)}")

    def _extract_images(self) -> None:
        """提取所有图片"""
        logger.info("开始提取epub中的所有图片")
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                image_id = item.id
                image_content = item.content
                image_name = unquote(item.file_name.split('/')[-1])
                logger.info(f"_extract_images——image_name: {image_name}")
                image_key = os.path.splitext(image_name)[0]
                logger.info(f"_extract_images——image_key: {image_key}")
                self.images[image_key] = {
                    'content': image_content,
                    'name': image_name,
                    'media_type': item.media_type
                }
        logger.info(f"成功提取 {len(self.images)} 张图片")

    def _write_metadata_to_file(self, file_path: str) -> None:
        """将元数据写入文件"""
        try:
            book_title = self.metadata.get('title', '未知书籍')
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {book_title}\n\n")
                f.write("## 图书信息\n\n")
                for key, value in self.metadata.items():
                    f.write(f"- **{key.capitalize()}**: {value}\n")
                f.write("\n## 目录\n\n")
            logger.info(f"成功写入元数据到文件: {file_path}")
        except Exception as e:
            logger.error(f"写入元数据失败: {str(e)}")

    def _save_images(self,output_dir:str) -> Dict[str,str]:
        """保存图片并返回路径映射"""
        image_paths = {}
        for image_id, image_data in self.images.items():
            try:
                safe_name = self.file_utils.clean_filename(image_data['name'])
                if not safe_name:
                    safe_name = f"image_{image_id}{self.image_processor.get_extension(image_data['media_type'])}"
                full_assets_dir = self.file_utils.create_directory(output_dir, ConverterConfig.assets)
                image_path = os.path.join(full_assets_dir, safe_name)
                image_name = safe_name.split('/')[-1].split('.')[0]
                image_key = os.path.splitext(image_name)[0]
                logger.info(f"image_path-----》: {image_key}")
                self.file_utils.write_file(image_path, image_data['content'])
                logger.info(f"image_name1-----》: {image_key}")
                image_paths[image_key] =f"./{ConverterConfig.assets}/{safe_name}" 
            except Exception as e:
                logger.error(f"保存图片 {image_key} 失败: {str(e)}")
        return image_paths

    def _convert_chapter_to_markdown(self, html_content: str, image_paths: Dict[str, str]) -> str:
        """将章节HTML转换为Markdown"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 处理图片路径
        for img in soup.find_all('img'):
            src = img.get('src', '')
            #image_id = src.split('/')[-1].split('.')[0]
            image_key = os.path.splitext(os.path.basename(src))[0]
            logger.info(f"image_name2-----》: {image_key}")
            if image_key in image_paths:
                img['src'] = image_paths[image_key]
                if not img.get('alt'):
                    img['alt'] = f"Image {image_key}"
        
        # 获取章节标题
        title = HtmlProcessor.get_chapter_title(soup)
        markdown = self.html2text.handle(str(soup))
        
        # 确保章节标题在开头
        if title and not markdown.startswith(f"# {title}"):
            markdown = f"# {title}\n\n{markdown}"
            
        return markdown

    def save_as_markdown(self, output_path: str) -> None:
        """保存为多个Markdown文件"""
        try:
            self._extract_metadata()
            self._extract_images()
            
            # 创建输出目录
            output_dir = output_path
            self.file_utils.create_directory("", output_dir)
            
            # 处理图片
         
            image_paths = self._save_images(output_path)
            
            # 创建README文件
            readme_path = os.path.join(output_dir, "README.md")
            self._write_metadata_to_file(readme_path)
            
            # 处理章节
            chapter_index = 1
            for item in tqdm(self.book.get_items()):
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    try:
                        content = item.get_content().decode('utf-8')
                        markdown = self._convert_chapter_to_markdown(content, image_paths)
                        chapter_filename = f"chapter_{chapter_index:03d}.md"
                        chapter_path = os.path.join(output_dir, chapter_filename)
                        
                        # 保存章节文件
                        self.file_utils.write_file(chapter_path, markdown.encode('utf-8'))
                        
                        # 更新目录
                        title = markdown.split('\n', 1)[0].lstrip('#').strip() or f"Chapter {chapter_index}"
                        with open(readme_path, "a", encoding="utf-8") as f:
                            f.write(f"- [{title}]({chapter_filename})\n")
                        
                        chapter_index += 1
                    except Exception as e:
                        logger.error(f"处理章节 {chapter_index} 失败: {str(e)}")
            
            logger.info(f"成功转换 {chapter_index-1} 个章节")
        except Exception as e:
            logger.error(f"转换失败: {str(e)}")
            raise

    def save_as_single_markdown(self, output_path: str) -> None:
        """保存为单个Markdown文件"""
        try:
            self._extract_metadata()
            self._extract_images()
            
            # 创建输出目录
            output_dir = os.path.dirname(output_path) or '.'
            self.file_utils.create_directory("", output_dir)
            
            # 处理图片
        #    assets_dir = self.file_utils.create_directory(output_dir, 'assets')
            image_paths = self._save_images(output_dir)
            
            # 写入内容
            with open(output_path, "w", encoding="utf-8") as f:
                # 写入元数据
                book_title = self.metadata.get('title', '未知书籍')
                f.write(f"# {book_title}\n\n")
                f.write("## 图书信息\n\n")
                for key, value in self.metadata.items():
                    f.write(f"- **{key.capitalize()}**: {value}\n")
                f.write("\n---\n\n")
                
                # 写入章节内容
                chapter_count = 0
                for item in tqdm(self.book.get_items()):
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        try:
                            content = item.get_content().decode('utf-8')
                            markdown = self._convert_chapter_to_markdown(content, image_paths)
                            f.write(f"\n{markdown}\n")
                            f.write("\n---\n\n")
                            chapter_count += 1
                        except Exception as e:
                            logger.error(f"处理章节 {chapter_count + 1} 失败: {str(e)}")
                
                logger.info(f"成功转换 {chapter_count} 个章节")
        except Exception as e:
            logger.error(f"转换失败: {str(e)}")
            raise

    def save_as_single_file_markdown(self, output_path: str) -> None:
        """保存为带Base64图片的单个Markdown文件"""
        try:
            self._extract_metadata()
            self._extract_images()
            
            # 转换图片为base64
            image_data = {
                image_id: self.image_processor.encode_to_base64(
                    image['content'], 
                    image['media_type']
                ) for image_id, image in self.images.items()
            }
            
            # 写入内容
            with open(output_path, "w", encoding="utf-8") as f:
                # 写入元数据
                book_title = self.metadata.get('title', '未知书籍')
                f.write(f"# {book_title}\n\n")
                f.write("## 图书信息\n\n")
                for key, value in self.metadata.items():
                    f.write(f"- **{key.capitalize()}**: {value}\n")
                f.write("\n---\n\n")
                
                # 写入章节内容
                chapter_count = 0
                for item in tqdm(self.book.get_items()):
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        try:
                            content = item.get_content().decode('utf-8')
                            soup = BeautifulSoup(content, 'html.parser')
                            
                            # 替换图片为base64
                            for img in soup.find_all('img'):
                                src = img.get('src', '')
                                image_key = os.path.splitext(os.path.basename(src))[0]
                                if image_key in image_data:
                                    img['src'] = image_data[image_key]
                            
                            markdown = self._convert_chapter_to_markdown(str(soup), {})
                            f.write(f"\n{markdown}\n")
                            f.write("\n---\n\n")
                            chapter_count += 1
                        except Exception as e:
                            logger.error(f"处理章节 {chapter_count + 1} 失败: {str(e)}")
                
                logger.info(f"成功转换 {chapter_count} 个章节")
        except Exception as e:
            logger.error(f"转换失败: {str(e)}")
            raise

    def convert(self, conversion_type: ConversionType, output_path: Optional[str] = None) -> None:
        """统一的转换入口"""
        if not self._ensure_book_loaded():
            return

        conversion_methods = {
            ConversionType.MULTIPLE_FILES: self.save_as_markdown,
            ConversionType.SINGLE_FILE: self.save_as_single_markdown,
            ConversionType.SINGLE_FILE_WITH_BASE64: self.save_as_single_file_markdown
        }

        method = conversion_methods.get(conversion_type)
        if method:
            method(output_path)
        else:
            raise ValueError(f"不支持的转换类型: {conversion_type}")

# ============= 使用示例 =============
def main():
    # 使用示例
    converter = EpubToMDConverter("file/日本蜡烛图技术epub.epub")
    
    # 转换为多个文件
    #converter.convert(ConversionType.MULTIPLE_FILES, "file/技术分析")
    
    # 转换为单个文件
    converter.convert(ConversionType.SINGLE_FILE, "file/技术分析.md")
    
    # 转换为带Base64图片的单个文件
    #converter.convert(ConversionType.SINGLE_FILE_WITH_BASE64, "file/biantaioutput_with_images.md")

if __name__ == "__main__":
    main()
import json
import re
import logging
from pathlib import Path
import argparse
from unstructured.partition.pdf import partition_pdf

# ========= 日志配置 =========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ========= 多书籍支持配置 =========
BOOKS = {
    "日本蜡烛图技术": {
        "pdf": "file/日本蜡烛图技术.pdf",
        "keywords": ["K线", "形态", "指标", "趋势", "反转", "突破", "支撑", "阻力", "成交量"],
        "source": "日本蜡烛图技术"
    },
    "金融市场技术分析": {
        "pdf": "file/市场技术分析.pdf",
        "keywords": ["趋势", "支撑", "阻力", "反转", "突破", "K线", "技术指标", "移动平均线", "MACD", "RSI"],
        "source": "金融市场技术分析"
    }
}

# ========= 工具函数 =========
def is_valid(text, keywords):
    if not (20 <= len(text) <= 500):
        return False
    if not any(kw in text for kw in keywords):
        return False
    if re.search(r"(免责声明|版权所有|扫码|www|http|出版社)", text):
        return False
    return True

def extract_chapter_title(text):
    match = re.match(r"^(第[一二三四五六七八九十百]+章)", text.strip())
    return match.group(1) if match else None

def extract_section_title(text):
    if len(text.strip()) <= 30 and any(kw in text for kw in ["形态", "模型", "K线", "趋势", "指标"]):
        return text.strip()
    return None

# ========= 主提取逻辑 =========
def process_book(book_name, config, debug=False):
    pdf_path = Path(config["pdf"])
    if not pdf_path.exists():
        logging.error(f"找不到PDF文件：{pdf_path}")
        return

    logging.info(f"📘 开始处理: {pdf_path.name}")

    elements = partition_pdf(filename=str(pdf_path), strategy="fast")
    results = []
    chapter = None
    section = None

    for element in elements:
        text = element.text.strip()
        if debug:
            logging.debug(f"🔍 提取文本: {text[:50]}")

        if not text:
            continue

        chapter_title = extract_chapter_title(text)
        if chapter_title:
            chapter = chapter_title
            continue

        section_title = extract_section_title(text)
        if section_title:
            section = section_title
            continue

        if not is_valid(text, config["keywords"]):
            if debug:
                logging.debug(f"❌ 无效文本: {text[:50]}")
            continue

        results.append({
            "text": text,
            "page": element.metadata.page_number,
            "chapter": chapter,
            "section_title": section,
            "source": config["source"]
        })

    output_path = Path("data") / f"{book_name}_term_et_action_input_v8.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logging.info(f"✅ {book_name} 提取完成，共 {len(results)} 条记录，已写入：{output_path}")

# ========= 主入口 =========
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="是否开启调试模式")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    for name, cfg in BOOKS.items():
        logging.info(f"📚 正在处理书籍：{name}")
        process_book(name, cfg, debug=args.debug)
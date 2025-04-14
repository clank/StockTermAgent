import fitz  # PyMuPDF
import re
import json
import logging
from pathlib import Path
from datetime import datetime
import argparse

# ========= 日志配置 =========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ========= 多书籍支持 =========
BOOKS = {
    "日本蜡烛图技术": {
        "pdf": "file/日本蜡烛图技术.pdf",
        "keywords": [
            "K线", "形态", "信号", "指标", "均线", "移动平均线", "反转", "突破",
            "支撑", "阻力", "成交量", "买入", "卖出", "头肩顶", "头肩底", "锤子线",
            "吞没形态", "黄昏星", "早晨星", "十字星", "跳空", "缺口", "MACD", "RSI",
            "布林带", "CCI", "SAR", "OBV", "DMI", "ATR", "实体", "影线",
            "顶部", "底部", "趋势", "上涨", "下跌"
        ],
        "source": "日本蜡烛图技术"
    },
    "金融市场技术分析": {
        "pdf": "file/市场技术分析.pdf",
        "keywords": [
            "支撑", "阻力", "突破", "反转", "趋势线", "成交量", "震荡", "动能",
            "震荡指标", "布林带", "K线", "技术指标", "移动平均线", "通道", "背离",
            "MACD", "RSI", "OBV", "形态", "上升三法", "下降三法", "图表形态",
            "头肩顶", "双底", "三角形", "旗形", "楔形", "矩形", "买入", "卖出"
        ],
        "source": "金融市场技术分析"
    }
}

# ========= 工具函数 =========
def extract_chapter_title(text):
    patterns = [
        r"^(第[一二三四五六七八九十百]+章)(\s|$)",
        r"^CHAPTER\s+\d+"
    ]
    for pat in patterns:
        match = re.match(pat, text.strip(), re.IGNORECASE)
        if match:
            return text.strip()
    return None

def extract_section_title(text):
    if len(text.strip()) <= 50 and any(kw in text for kw in ["形态", "模型", "K线", "线图", "指标", "趋势"]):
        return text.strip()
    return None

def extract_figure(text):
    match = re.search(r"(图\d+(\.\d+)?|Figure\s+\d+(\.\d+)?)", text, re.IGNORECASE)
    return match.group(1) if match else None

def classify_type(text):
    if re.match(r".*?[是为指称叫属于构成]+.*?一种.*?[形态模型结构]?", text):
        return "定义"
    elif any(x in text for x in ["买入", "卖出", "信号", "建议", "触发", "策略"]):
        return "交易逻辑"
    elif extract_figure(text):
        return "图注"
    elif len(text) <= 60 and any(kw in text for kw in ["形态", "模型", "K线", "指标"]):
        return "术语"
    else:
        return "说明"

def is_valid(text, keywords):
    if not (15 <= len(text) <= 500):
        return False
    if not any(kw in text for kw in keywords):
        return False
    if re.search(r"(免责声明|版权所有|微信|扫码|www\.|http|大学|出版社|图表来源|技术支持)", text):
        return False
    if text.endswith("：") or len(text.split()) < 2:
        return False
    return True

def merge_lines(lines, max_len=120):
    paragraph = ""
    for line in lines:
        if paragraph:
            paragraph += " " + line.strip()
        else:
            paragraph = line.strip()
        if len(paragraph) >= max_len:
            yield paragraph
            paragraph = ""
    if paragraph:
        yield paragraph

# ========= 主提取逻辑 =========
def process_book(book_name, config, debug=False):
    pdf_path = Path(config["pdf"])
    if not pdf_path.exists():
        logging.warning(f"❌ 找不到PDF文件：{pdf_path}")
        return

    logging.info(f"📘 开始处理: {pdf_path.name}")
    keywords = config["keywords"]
    source = config["source"]

    results = []
    buffer = []
    chapter = None
    section = None

    doc = fitz.open(pdf_path)
    for page in doc:
        page_number = page.number + 1
        blocks = page.get_text("blocks")
        lines = [line.strip() for block in blocks for line in block[4].split("\n") if line.strip()]

        for para in merge_lines(lines):
            chapter_title = extract_chapter_title(para)
            if chapter_title:
                chapter = chapter_title
                continue

            section_title = extract_section_title(para)
            if section_title:
                section = section_title
                continue

            if debug:
                logging.debug(f"🧪 Raw para: {para}")

            if not is_valid(para, keywords):
                if debug:
                    logging.debug(f"❌ 无效段落: {para}")
                continue

            fig = extract_figure(para)
            ptype = classify_type(para)

            if debug:
                logging.debug(f"✅ 有效段落: {para} | 类型: {ptype} | 页码: {page_number}")

            if ptype == "图注":
                buffer.append({
                    "text": para,
                    "page": page_number,
                    "chapter": chapter,
                    "section_title": section,
                    "figure": fig,
                    "type": ptype,
                    "source": source
                })
                continue

            if buffer:
                fig_entry = buffer.pop()
                fig_entry.update({
                    "text_full": fig_entry["text"] + " " + para,
                    "from_figure_merge": True,
                    "context_window": [],
                    "page": page_number,
                    "chapter": chapter,
                    "section_title": section
                })
                results.append(fig_entry)
            else:
                entry = {
                    "text": para,
                    "page": page_number,
                    "chapter": chapter,
                    "section_title": section,
                    "figure": fig,
                    "type": ptype,
                    "context_window": [r["text"] for r in results[-2:]] if len(results) >= 2 else [],
                    "source": source
                }
                results.append(entry)

    output_path = Path("data") / f"{book_name}_term_et_action_input_v7.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    logging.info(f"✅ 写入 {len(results)} 条记录至：{output_path}")

# ========= 主入口 =========
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="是否开启调试日志")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    for name, cfg in BOOKS.items():
        logging.info(f"📖 正在处理书籍：{name}")
        process_book(name, cfg, debug=args.debug)
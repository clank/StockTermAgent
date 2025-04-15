import fitz
import re
import json
import logging
from enum import Enum

# ====== 路径配置 ======
pdf_paths = [
    # "file/金融市场技术分析.pdf",
    "file/日本蜡烛图技术.pdf"
]
output_jsonl = "data/term_et_action_input_data_v4.jsonl"

# ====== 日志配置 ======
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ====== 股票语言关键词 (合并两本书的关键词) ======
keywords = [
    "K线", "形态", "信号", "指标", "均线", "移动平均线", "反转", "突破",
    "支撑", "阻力", "成交量", "买入", "卖出", "头肩顶", "头肩底", "锤子线",
    "吞没形态", "乌云盖顶", "刺透形态", "启明星", "黄昏星", "十字星", "流星线",
    "倒锤子线", "孕线", "平头顶部", "平头底部", "捉腰带线", "三只乌鸦", "白色三兵",
    "三山形态", "三川形态", "反击线", "约会线", "圆形顶部", "圆形底部", "塔形顶部",
    "塔形底部", "窗口", "跳空", "上升三法", "下降三法", "分手线", "十字线", "长腿十字线",
    "墓碑十字线", "蜻蜓十字线", "三星形态", "趋势线", "百分比回撤", "摆动指数", "RSI",
    "MACD", "布林带", "CCI", "SAR", "OBV", "DMI", "ATR", "艾略特波浪", "黄金分割",
    "回撤", "整理", "巩固", "超买", "超卖", "背离", "发散", "收敛", "箱体", "通道",
    "扇形", "时间周期", "循环周期", "换手率", "板块轮动", "交叉市场分析"
]

# ====== 正则表达式模式 ======
CHAPTER_TITLE_PATTERN = re.compile(r"^(第[一二三四五六七八九十百]+章)(\s|$)")
SECTION_TITLE_PATTERN = re.compile(r"^((\d+\.)*\d+\s)?[\u4e00-\u9fa5_a-zA-Z0-9]+(：|:| )")
FIGURE_PATTERN = re.compile(r"(图\s*\d+(-\d+)?)")
DEFINITION_PATTERN = re.compile(r".*?[是为指称叫属于构成]+.*?一种.*?[形态模型结构]?", re.IGNORECASE)
ACTION_PATTERN = re.compile(r".*(买入|卖出|信号|建议|策略|触发).*")

# ====== 类型枚举 ======
class EntryType(str, Enum):
    DEFINITION = "定义"
    TRADING_LOGIC = "交易逻辑"
    FIGURE_CAPTION = "图注"
    TERM = "术语"
    EXPLANATION = "说明"

# ====== 提取章节标题 ======
def extract_chapter_title(text):
    match = CHAPTER_TITLE_PATTERN.match(text.strip())
    if match:
        return match.group(1)
    return None

# ====== 提取小节标题 ======
def extract_section_title(text):
    if len(text.strip()) <= 50:
        match = SECTION_TITLE_PATTERN.match(text)
        if match:
            return text.strip()
    return None

# ====== 提取图号 ======
def extract_figure(text):
    match = FIGURE_PATTERN.search(text)
    if match:
        return match.group(1)
    return None

# ====== 识别类型 ======
def classify_type(text):
    if DEFINITION_PATTERN.search(text):
        return EntryType.DEFINITION
    elif ACTION_PATTERN.search(text):
        return EntryType.TRADING_LOGIC
    elif extract_figure(text):
        return EntryType.FIGURE_CAPTION
    elif len(text) <= 40 and any(kw in text for kw in ["形态", "模型", "K线", "线图", "指标", "术语"]):
        return EntryType.TERM
    else:
        return EntryType.EXPLANATION

# ====== 判断有效性 ======
def is_valid(text):
    text = text.strip()
    if not (20 <= len(text) <= 500):
        return False
    if not any(kw in text for kw in keywords):
        return False
    if re.search(r"(免责声明|版权所有|微信|扫码|www\.|http|\.cn|大学|出版社|本书由)", text):
        return False
    if text.endswith("：") or len(text.split()) < 3:
        return False
    return True

# ====== 主提取逻辑 ======
def extract_data(pdf_paths):
    results = []
    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
        source = pdf_path.split("/")[-1].replace(".pdf", "")  # 获取文件名作为来源
        buffer = []
        current_chapter = None
        current_section = None

        for page in doc:
            page_number = page.number + 1
            blocks = page.get_text("blocks")
            for block in blocks:
                for line in block[4].split("\n"):
                    text = line.strip()
                    if not text:
                        continue

                    # 检测章节、小节
                    chapter_title = extract_chapter_title(text)
                    if chapter_title:
                        current_chapter = chapter_title
                        logging.info(f"章节标题：{current_chapter}，来源：{source}")
                        continue

                    section_title = extract_section_title(text)
                    if section_title:
                        current_section = section_title
                        logging.info(f"小节标题：{current_section}，来源：{source}")
                        continue

                    # 检测合法段落
                    if not is_valid(text):
                        continue

                    fig_id = extract_figure(text)
                    entry_type = classify_type(text)

                    # 图段进入缓冲
                    if entry_type == EntryType.FIGURE_CAPTION:
                        buffer.append({
                            "text": text,
                            "page": page_number,
                            "chapter": current_chapter,
                            "section_title": current_section,
                            "figure": fig_id,
                            "type": entry_type.value,
                            "source": source
                        })
                        continue

                    # 补全图注（合并下段）
                    if buffer:
                        fig_entry = buffer.pop()
                        fig_entry["text_full"] = fig_entry["text"] + " " + text
                        fig_entry["from_figure_merge"] = True
                        fig_entry["context_window"] = []
                        fig_entry["page"] = page_number
                        fig_entry["chapter"] = current_chapter
                        fig_entry["section_title"] = current_section
                        fig_entry["source"] = source
                        results.append(fig_entry)
                    else:
                        entry = {
                            "text": text,
                            "page": page_number,
                            "chapter": current_chapter,
                            "section_title": current_section,
                            "figure": fig_id,
                            "type": entry_type.value,
                            "context_window": [r["text"] for r in results[-2:]] if len(results) >= 2 else [],
                            "source": source
                        }
                        results.append(entry)
                    logging.debug(f"提取内容：{entry}，来源：{source}")
        doc.close()
    return results

# ====== 写入输出文件 ======
def write_to_jsonl(data, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logging.info(f"✅ 共提取 {len(data)} 条结构化段，写入文件：{output_path}")

if __name__ == "__main__":
    extracted_data = extract_data(pdf_paths)
    write_to_jsonl(extracted_data, output_jsonl)
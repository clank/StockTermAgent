import fitz  # PyMuPDF
import re
import json

# ====== 路径配置 ======
pdf_path = "file/日本蜡烛图技术.pdf"
output_jsonl = "data/term_et_action_input_data.jsonl"

# ====== 股票语言关键词 ======
keywords = [
    "K线", "形态", "信号", "指标", "均线", "移动平均线", "反转", "突破",
    "支撑", "阻力", "成交量", "买入", "卖出", "头肩顶", "头肩底", "锤子线",
    "吞没形态", "黄昏星", "早晨星", "十字星", "跳空", "缺口", "MACD", "RSI",
    "布林带", "CCI", "SAR", "OBV", "DMI", "ATR", "实体", "影线",
    "顶部", "底部", "趋势", "上涨", "下跌"
]

# ====== 标题提取逻辑 ======
def extract_chapter_title(text):
    match = re.match(r"^(第[一二三四五六七八九十百]+章)(\s|$)", text.strip())
    return match.group(1) if match else None

def extract_section_title(text):
    if len(text.strip()) <= 25 and any(kw in text for kw in ["形态", "模型", "K线", "线图", "指标"]):
        return text.strip()
    return None

# ====== 图号提取 ======
def extract_figure(text):
    match = re.search(r"(图\d+(\.\d+)?)", text)
    return match.group(1) if match else None

# ====== 类型识别逻辑 ======
def classify_type(text):
    if re.match(r".*?[是为指称叫属于构成]+.*?一种.*?[形态模型结构]?", text):
        return "定义"
    elif any(x in text for x in ["买入", "卖出", "信号", "建议", "触发", "策略"]):
        return "交易逻辑"
    elif extract_figure(text):
        return "图注"
    elif len(text) <= 40 and any(kw in text for kw in ["形态", "模型", "K线", "指标"]):
        return "术语"
    else:
        return "说明"

# ====== 有效性判断 ======
def is_valid(text):
    if not (25 <= len(text) <= 350):
        return False
    if not any(kw in text for kw in keywords):
        return False
    if re.search(r"(免责声明|版权所有|微信|扫码|www\.|http|\.cn|大学|出版社)", text):
        return False
    if text.endswith("：") or len(text.split()) < 3:
        return False
    return True

# ====== 主提取逻辑 ======
doc = fitz.open(pdf_path)
results = []
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
                continue

            section_title = extract_section_title(text)
            if section_title:
                current_section = section_title
                continue

            # 检测合法段落
            if not is_valid(text):
                continue

            fig_id = extract_figure(text)
            ptype = classify_type(text)

            # 图段进入缓冲
            if ptype == "图注":
                buffer.append({
                    "text": text,
                    "page": page_number,
                    "chapter": current_chapter,
                    "section_title": current_section,
                    "figure": fig_id,
                    "type": ptype,
                    "source": "日本蜡烛图技术"
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
                fig_entry["source"] = "日本蜡烛图技术"
                results.append(fig_entry)
            else:
                entry = {
                    "text": text,
                    "page": page_number,
                    "chapter": current_chapter,
                    "section_title": current_section,
                    "figure": fig_id,
                    "type": ptype,
                    "context_window": [r["text"] for r in results[-2:]] if len(results) >= 2 else [],
                    "source": "日本蜡烛图技术"
                }
                results.append(entry)

# ====== 写入输出文件 ======
with open(output_jsonl, "w", encoding="utf-8") as f:
    for item in results:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"✅ 共提取 {len(results)} 条结构化段，写入文件：{output_jsonl}")
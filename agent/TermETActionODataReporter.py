import json
import os
import logging

# 文件路径
INPUT_FILE = "data/term_et_action_output_data.jsonl"
OUTPUT_MD_FILE = "data/term_et_action_cards.md"
ERROR_LOG_FILE = "log/error_lines.log"
REPORT_LOG_FILE="log/term_et_action_report.log"


# 设置日志配置
logging.basicConfig(
    filename='data/conversion.log',
    filemode='w',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    encoding='utf-8'
)

# 渲染单张知识卡片为 Markdown
def render_card(card_json):
    return f"""
## 📘 {card_json.get("indicator_name", "未命名指标")}

- **图示**：{card_json.get("figure_ref", "无")}
- **定义**：
  > {card_json.get("definition", "无定义")}
- **信号逻辑**：
  > {card_json.get("signal_logic", "无信号逻辑")}

### ❓ 问答：
""" + "\n".join([
        f"- **Q**: {qa.get('Q', '无问题')}\n  - **A**: {qa.get('A', '无答案')}"
        for qa in card_json.get("qa_pairs", [])
    ])

# 主函数
def main():
    if not os.path.exists(INPUT_FILE) or os.path.getsize(INPUT_FILE) == 0:
        logging.error("输入文件为空或不存在。")
        print("❌ 输入文件为空或不存在，请检查路径或内容。")
        return

    cards = []
    error_lines = []

    with open(INPUT_FILE, "r", encoding="utf-8") as infile:
        for i, line in enumerate(infile):
            try:
                if not line.strip():
                    continue
                entry = json.loads(line)

                if isinstance(entry.get("output"), str) and entry["output"].startswith("```json"):
                    json_str = entry["output"].strip("`json\n").rstrip("`").strip()
                    card_json = json.loads(json_str)
                    cards.append(render_card(card_json))
                    logging.info(f"✅ 第{i+1}行转换成功：{card_json.get('indicator_name', '未知')}")
                else:
                    raise ValueError("output 字段不是预期格式")

            except Exception as e:
                logging.warning(f"⚠️ 第{i+1}行转换失败：{e}")
                error_lines.append(f"Line {i+1}: {line.strip()}")

    if error_lines:
        with open(ERROR_LOG_FILE, "w", encoding="utf-8") as errlog:
            errlog.write("\n".join(error_lines))
        logging.warning(f"⚠️ 有 {len(error_lines)} 行出错，详情见 {ERROR_LOG_FILE}")

    if not cards:
        logging.error("⚠️ 没有成功生成任何卡片。")
        print("⚠️ 没有生成任何有效卡片，请检查日志。")
        return

    with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("# 📚 股票术语知识卡片\n\n")
        outfile.write("\n---\n".join(cards))

    logging.info(f"✅ 成功生成 {len(cards)} 张卡片，已写入 {OUTPUT_MD_FILE}")
    print(f"✅ 生成完成，{len(cards)} 张卡片已写入 {OUTPUT_MD_FILE}")

if __name__ == "__main__":
    main()

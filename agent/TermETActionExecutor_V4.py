import json
import time
import os
import argparse
from http import HTTPStatus
from dotenv import load_dotenv
from dashscope import Application

# 加载 .env 文件
load_dotenv()

# 从 .env 中读取配置
API_KEY = os.getenv("BAILIAN_API_KEY")
APP_ID = os.getenv("BAILIAN_APP_ID")

assert API_KEY, "请在 .env 文件中设置 BAILIAN_API_KEY"
assert APP_ID, "请在 .env 文件中设置 BAILIAN_APP_ID"

INPUT_FILE = "data/金融市场技术分析_term_et_action_input_v7.jsonl"
OUTPUT_FILE = "data/金融市场技术分析_term_et_action_output_v9.jsonl"


# Prompt 构建模板
def build_prompt(entry):
    base_prompt = f"""你是一个“股票术语分析助手”，专门负责从金融技术分析类书籍中提取【技术术语卡片】。
你的目标是提取与K线图形态、技术指标、交易信号或分析方法相关的术语及其定义和使用逻辑，并为用户构建结构化知识卡片，便于索引、检索与问答。

请根据以下说明完成任务：

【任务要求】
1. 自动识别输入段落是否属于“股票技术术语”说明，如K线形态、趋势指标、信号逻辑等；
2. 如果包含术语信息，按以下格式输出完整结构卡片；
3. 如果是导言、图书目录或无术语的段落，仅生成 `qa_pairs` 字段，其他字段留空；
4. 若信息不足，可合理补全术语逻辑，保持真实但不虚构；
5. 严格输出为可解析 JSON 字符串，格式见下方。

【输出格式】
```json
{{
  "indicator_name": "术语名称（如：头肩顶、RSI、趋势线等）",
  "definition": "简洁定义，说明它是什么",
  "signal_logic": "它在交易中的使用逻辑或触发条件",
  "figure_ref": "图号或图示引用（如有）",
  "qa_pairs": [
    {{ "Q": "问题1", "A": "答案1" }},
    {{ "Q": "问题2", "A": "答案2" }}
  ]
}}

请分析下列段落：
{entry.get('text_full') or entry.get('text')}
"""
    return base_prompt

# 主逻辑
def main(max_count=None):
    with open(INPUT_FILE, "r", encoding="utf-8") as infile, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

        for idx, line in enumerate(infile):
            if max_count is not None and idx >= max_count:
                print(f"🚫 已达到最大处理数量 {max_count}，提前结束。")
                break

            try:
                entry = json.loads(line.strip())
                prompt = build_prompt(entry)

                print(f"📨 正在处理第 {idx + 1} 段：{entry['text'][:50]}...")

                response = Application.call(
                    api_key=API_KEY,
                    app_id=APP_ID,
                    prompt=prompt
                )

                result = {
                    "input": entry.get("text_full") or entry.get("text"),
                    "output": response.output.text if response.status_code == HTTPStatus.OK else "ERROR",
                    "error": None if response.status_code == HTTPStatus.OK else {
                        "code": response.status_code,
                        "message": response.message,
                        "request_id": response.request_id
                    }
                }

                if response.status_code == HTTPStatus.OK:
                    print("✅ 成功")
                else:
                    print(f"❌ 错误: {response.status_code} - {response.message}")

                outfile.write(json.dumps(result, ensure_ascii=False) + "\n")
                time.sleep(1)  # 控制请求频率

            except Exception as e:
                print(f"⚠️ 处理第 {idx + 1} 段失败：{e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="结构化技术分析段落")
    parser.add_argument("--max-count", type=int, default=None, help="最大处理条数，默认不限制")
    args = parser.parse_args()
    main(max_count=args.max_count)

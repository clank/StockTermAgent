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

# Prompt 构建模板
def build_prompt(entry):
    base_prompt = f"""你是一个金融结构化分析Agent，当前任务是从段落中抽取K线图形态或技术指标的结构化信息。
请按如下格式输出JSON：
{{
  "indicator_name": "...",
  "definition": "...",
  "signal_logic": "...",
  "figure_ref": "...",
  "qa_pairs": [
    {{
      "Q": "...",
      "A": "..."
    }}
  ]
}}

请分析下列段落：
{entry.get('text_full') or entry.get('text')}
"""
    return base_prompt

# 主逻辑函数
def main(input_file, output_file, max_count=None):
    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "w", encoding="utf-8") as outfile:

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
                time.sleep(1)

            except Exception as e:
                print(f"⚠️ 处理第 {idx + 1} 段失败：{e}")

# 启动入口，支持命令行参数
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="结构化技术分析段落")
    parser.add_argument("--input-file", type=str, default="data/term_et_action_input_data.jsonl", help="输入文件路径")
    parser.add_argument("--output-file", type=str, default="data/term_et_action_output_data.jsonl", help="输出文件路径")
    parser.add_argument("--max-count", type=int, default=None, help="最大处理条数，默认不限制")

    args = parser.parse_args()
    main(input_file=args.input_file, output_file=args.output_file, max_count=args.max_count)
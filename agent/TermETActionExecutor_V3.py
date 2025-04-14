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

INPUT_FILE = "data/term_et_action_input_data.jsonl"
OUTPUT_FILE = "data/term_et_action_output_data.jsonl"


# Prompt 构建模板
def build_prompt(entry):
    base_prompt = f"""你是一个擅长结构化金融技术分析语言的 AI Agent,专门从技术分析文档中提取蜡烛图相关指标的结构化信息。你的任务是：根据输入内容，抽取一个清晰、结构化的蜡烛图技术指标信息，并按如下格式输出JSON：
{{
  "indicator_name": "...", // 指标名称，例如“看跌吞没形态”
  "definition": "...",  // 指标定义，说明该指标本身的含义和构成
  "signal_logic": "...", // 信号逻辑：说明它在交易中代表什么信号（如买入/卖出/反转/持续）
  "figure_ref": "...", // 若输入中含有图示（如“图6.57”），填入图号，否则填空字符串
  "qa_pairs": [    // 至少生成2个“问答对”，用于增强知识库中的问答能力
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

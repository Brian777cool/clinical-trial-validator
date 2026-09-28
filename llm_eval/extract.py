"""用 OpenAI API 從 30 份模擬病歷抽取收案欄位，輸出 extractions.jsonl。

使用前：
    pip install openai
    （PowerShell）$env:OPENAI_API_KEY = "你的新 key"     ← 只在目前這個終端機有效，不會存進檔案

用法：
    python extract.py                       # 預設模型
    python extract.py --model gpt-4o-mini   # 指定模型（請用你帳號可使用的模型名稱）

已經抽過的病歷會跳過，所以中途中斷可以直接重跑。
"""
import argparse
import json
import os
import sys
import time

from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ["patient_id", "platelet_count", "bilirubin", "albumin", "inr", "ecw_ratio", "phase_angle",
          "tumor_length_cm", "tumor_width_cm", "tumor_height_cm", "ascites", "encephalopathy"]


def load_done(path):
    done = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                done.add(json.loads(line)["patient_id"])
    return done


def extract_one(client, model, prompt, patient_id):
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            data = json.loads(response.choices[0].message.content)
            data["patient_id"] = patient_id  # 以檔案中的 ID 為準
            return {field: data.get(field, "MISSING") for field in FIELDS}
        except Exception as e:  # 網路錯誤、格式錯誤等，稍等後重試
            print(f"  {patient_id} 第 {attempt + 1} 次失敗：{e}")
            time.sleep(3)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--output", default="extractions.jsonl")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("找不到環境變數 OPENAI_API_KEY，請先設定。")

    client = OpenAI()
    template = open(os.path.join(HERE, "extraction_prompt.md"), encoding="utf-8").read()
    notes = [json.loads(l) for l in open(os.path.join(HERE, "synthetic_notes.jsonl"), encoding="utf-8") if l.strip()]
    output_path = os.path.join(HERE, args.output)
    done = load_done(output_path)

    with open(output_path, "a", encoding="utf-8") as out:
        for item in notes:
            pid = item["patient_id"]
            if pid in done:
                continue
            print(f"抽取 {pid} ...")
            result = extract_one(client, args.model, template.replace("{{NOTE}}", item["note"]), pid)
            if result is None:
                print(f"  {pid} 失敗，略過（重跑時會再試）")
                continue
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()

    with open(os.path.join(HERE, "run_info.json"), "w", encoding="utf-8") as f:
        json.dump({"model": args.model, "temperature": 0,
                   "date": time.strftime("%Y-%m-%d")}, f, ensure_ascii=False, indent=2)
    print(f"完成，結果在 {args.output}；模型資訊記在 run_info.json")


if __name__ == "__main__":
    main()
    
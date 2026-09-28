"""評估 LLM 抽取結果：逐欄位比對標準答案，並把抽取結果送進 validator 看最終判定。

用法（在 llm_eval 資料夾內）：
    python evaluate.py extractions.jsonl

本程式會自動找到 repo 裡的 validator.py，並改用本資料夾的 emr_rows_P3000.csv 作為核對用的 EMR，
不需要修改 scripts/mock_emr_db.csv。
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATOR_DIR = os.path.join(HERE, "..", "skills", "open-trial-validator-Brian777cool", "scripts")
sys.path.insert(0, os.path.abspath(VALIDATOR_DIR))

import validator  # noqa: E402
from validator import validate_trial  # noqa: E402

# 評估時只用本資料夾的 30 筆模擬 EMR
validator.EMR_DB_PATH = os.path.join(HERE, "emr_rows_P3000.csv")

FIELDS = ["platelet_count", "bilirubin", "albumin", "inr", "ecw_ratio", "phase_angle",
          "tumor_length_cm", "tumor_width_cm", "tumor_height_cm", "ascites", "encephalopathy"]
# 與 validator.py 相同的容許誤差（報告精度的一半）
TOLERANCE = {"bilirubin": 0.05, "albumin": 0.05, "inr": 0.005, "ecw_ratio": 0.005,
             "phase_angle": 0.05, "tumor_length_cm": 0.05, "tumor_width_cm": 0.05,
             "tumor_height_cm": 0.05}


def same(field, truth, pred):
    if truth == "MISSING" or pred in (None, "", "MISSING"):
        return str(truth) == str(pred if pred not in (None, "") else "MISSING")
    if field in ("ascites", "encephalopathy"):
        return str(pred).strip() == truth
    try:
        if field == "platelet_count":
            return int(float(pred)) == int(truth)
        return round(abs(float(pred) - float(truth)), 6) <= TOLERANCE[field]
    except (ValueError, TypeError):
        return False


def main(path):
    truth = {r["patient_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "ground_truth.csv"), encoding="utf-8"))}
    preds = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            p = json.loads(line)
            preds[p["patient_id"]] = p

    field_correct = {f: 0 for f in FIELDS}
    hallucinated, missed_values, rows = 0, 0, []
    for pid, t in truth.items():
        p = preds.get(pid, {})
        errors = []
        for f in FIELDS:
            ok = same(f, t[f], p.get(f))
            field_correct[f] += ok
            if not ok:
                errors.append(f"{f}: 答案 {t[f]} / 抽取 {p.get(f)}")
                if t[f] == "MISSING":
                    hallucinated += 1      # 病歷沒寫，LLM 卻給了值
                elif p.get(f) in (None, "", "MISSING"):
                    missed_values += 1     # 病歷有寫，LLM 卻說缺漏
        record = {k: v for k, v in p.items() if v not in (None, "", "MISSING")}
        is_valid, result = validate_trial(record)
        verdict = "ELIGIBLE" if is_valid else str(result).split("（")[0].split(":")[0]
        rows.append([pid, t["tier"], len(errors), verdict, "；".join(errors)])

    n = len(truth)
    print("欄位正確率：")
    for f in FIELDS:
        print(f"  {f:16s} {field_correct[f]}/{n} = {field_correct[f]/n:.1%}")
    perfect = sum(1 for r in rows if r[2] == 0)
    print(f"整份完全正確：{perfect}/{n}")
    print(f"幻覺（病歷未記載卻給值）：{hallucinated} 個欄位")
    print(f"漏抽（病歷有記載卻標缺漏）：{missed_values} 個欄位")

    with open(os.path.join(HERE, "evaluation_result.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["patient_id", "tier", "錯誤欄位數", "validator 判定", "錯誤明細"])
        w.writerows(rows)
    print("逐筆結果已存成 evaluation_result.csv，可和 expected_outcome.csv 對照。")


if __name__ == "__main__":
    main(sys.argv[1])